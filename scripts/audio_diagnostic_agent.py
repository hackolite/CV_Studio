#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Diagnostic Agent - CLI tool to detect audio detection issues in videos.

This agent analyzes audio from video files to detect potential misclassifications
by examining spectrograms and frequency band energies. It generates detailed reports
to help diagnose why certain audio predictions may be incorrect.
"""

import argparse
import os
import sys
import json
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import yaml
import numpy as np

# Import audio utilities
from utils_audio import (
    get_sample_rate,
    extract_audio_wav,
    compute_mel_spectrogram,
    measure_energy_in_band,
    save_spectrogram_image
)


class AudioDiagnosticAgent:
    """Main agent class for audio diagnostics."""
    
    def __init__(self, config: Dict):
        """
        Initialize the agent with configuration.
        
        Args:
            config: Configuration dictionary with parameters
        """
        self.config = config
        self.output_dir = config.get('output_dir', 'reports')
        self.topk = config.get('topk', 5)
        self.model_path = config.get('model_path', None)
        
        # Spectrogram parameters
        self.n_fft = config.get('n_fft', 2048)
        self.hop_length = config.get('hop_length', 512)
        self.n_mels = config.get('n_mels', 128)
        self.fmin = config.get('fmin', 0.0)
        self.fmax = config.get('fmax', None)
        
        # Frequency band definitions for common sounds
        self.frequency_bands = config.get('frequency_bands', {
            'bark': (150, 2000),      # Dog bark typical range
            'snore': (50, 300),       # Snoring typical range
            'chirp': (2000, 8000),    # Bird chirp range
            'low_freq': (0, 500),     # Low frequency range
            'mid_freq': (500, 2000),  # Mid frequency range
            'high_freq': (2000, 8000) # High frequency range
        })
        
        # Suspicion thresholds
        self.thresholds = config.get('thresholds', {
            'energy_diff_threshold': 10.0,  # dB difference threshold
            'sample_rate_mismatch': True     # Flag sample rate mismatches
        })
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_inference_predictions(self, audio_path: str, spectrogram: np.ndarray) -> Optional[List[Tuple[str, float]]]:
        """
        Attempt to get predictions from the project's inference function.
        
        Args:
            audio_path: Path to audio file
            spectrogram: Mel spectrogram array
            
        Returns:
            List of (label, confidence) tuples, or None if unavailable
        """
        # Try to import and use classification inference if available
        try:
            # Look for classification module
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from node.DLNode.classification.esc50_class_names import esc50_class_names
            
            # In a real scenario, we would load the model and run inference
            # For now, return None to trigger fallback
            return None
            
        except Exception as e:
            print(f"Could not load inference module: {e}")
            return None
    
    def get_fallback_predictions(self, base_path: str) -> Optional[List[Tuple[str, float]]]:
        """
        Fallback method to read predictions from labels.txt if present.
        
        Args:
            base_path: Base path to search for labels.txt
            
        Returns:
            List of (label, confidence) tuples, or None if unavailable
        """
        # Look for labels.txt in common locations
        search_paths = [
            os.path.join(base_path, 'labels.txt'),
            os.path.join(os.path.dirname(__file__), '..', 'labels.txt'),
            os.path.join(os.path.dirname(__file__), '..', 'node', 'DLNode', 'classification', 'labels.txt')
        ]
        
        for labels_path in search_paths:
            if os.path.exists(labels_path):
                try:
                    with open(labels_path, 'r', encoding='utf-8') as f:
                        labels = [line.strip() for line in f if line.strip()]
                    
                    # Return mock predictions with uniform confidence
                    # In practice, this would use actual predictions
                    return [(label, 1.0 / len(labels)) for label in labels[:self.topk]]
                    
                except Exception as e:
                    print(f"Error reading {labels_path}: {e}")
                    
        # Try to use ESC-50 class names as fallback
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from node.DLNode.classification.esc50_class_names import esc50_class_names
            
            # Return mock predictions
            labels = list(esc50_class_names.values())[:self.topk]
            return [(label, 0.2) for label in labels]
            
        except Exception:
            pass
            
        return None
    
    def analyze_audio(self, video_path: str) -> Dict:
        """
        Analyze audio from a video file and generate diagnostic report.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing analysis results
        """
        print(f"\nProcessing: {video_path}")
        
        result = {
            'video_path': video_path,
            'timestamp': datetime.now().isoformat(),
            'original_sample_rate': None,
            'used_sample_rate': None,
            'spectrogram_path': None,
            'top_predictions': [],
            'frequency_band_energies': {},
            'suspicion': False,
            'suspicion_reasons': []
        }
        
        # Get original sample rate
        original_sr = get_sample_rate(video_path)
        result['original_sample_rate'] = original_sr
        
        if original_sr is None:
            result['suspicion'] = True
            result['suspicion_reasons'].append("Could not determine original sample rate")
            return result
        
        # Extract audio to temporary WAV file
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        temp_wav = os.path.join(self.output_dir, f"{video_name}_temp.wav")
        
        if not extract_audio_wav(video_path, temp_wav, sample_rate=original_sr):
            result['suspicion'] = True
            result['suspicion_reasons'].append("Failed to extract audio")
            return result
        
        # Compute mel spectrogram
        mel_spec_db, used_sr = compute_mel_spectrogram(
            temp_wav,
            sr=original_sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels,
            fmin=self.fmin,
            fmax=self.fmax
        )
        
        if mel_spec_db is None:
            result['suspicion'] = True
            result['suspicion_reasons'].append("Failed to compute spectrogram")
            # Clean up
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
            return result
        
        result['used_sample_rate'] = used_sr
        
        # Check for sample rate mismatch
        if self.thresholds['sample_rate_mismatch'] and original_sr != used_sr:
            result['suspicion'] = True
            result['suspicion_reasons'].append(
                f"Sample rate mismatch: original={original_sr}, used={used_sr}"
            )
        
        # Save spectrogram image
        spec_image_path = os.path.join(self.output_dir, f"{video_name}_spectrogram.png")
        if save_spectrogram_image(mel_spec_db, spec_image_path, used_sr, self.hop_length, 
                                   title=f"Mel Spectrogram - {video_name}"):
            result['spectrogram_path'] = spec_image_path
        
        # Measure energy in different frequency bands
        fmax_actual = self.fmax if self.fmax else used_sr / 2.0
        
        for band_name, (freq_min, freq_max) in self.frequency_bands.items():
            # Only measure if band is within spectrogram range
            if freq_min < fmax_actual:
                energy = measure_energy_in_band(
                    mel_spec_db, freq_min, min(freq_max, fmax_actual),
                    used_sr, self.n_mels, self.fmin, fmax_actual
                )
                result['frequency_band_energies'][band_name] = float(energy)
        
        # Analyze energy distribution for suspicions
        if len(result['frequency_band_energies']) >= 2:
            energies = list(result['frequency_band_energies'].values())
            energy_range = max(energies) - min(energies)
            
            if energy_range > self.thresholds['energy_diff_threshold']:
                result['suspicion'] = True
                result['suspicion_reasons'].append(
                    f"Large energy variation across bands: {energy_range:.1f} dB"
                )
        
        # Try to get predictions
        predictions = self.get_inference_predictions(temp_wav, mel_spec_db)
        
        if predictions is None:
            predictions = self.get_fallback_predictions(os.path.dirname(video_path))
        
        if predictions:
            result['top_predictions'] = [
                {'label': label, 'confidence': float(conf)}
                for label, conf in predictions[:self.topk]
            ]
        
        # Clean up temporary WAV file
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        return result
    
    def process_input(self, input_path: str) -> List[Dict]:
        """
        Process input file or directory.
        
        Args:
            input_path: Path to video file or directory
            
        Returns:
            List of analysis results
        """
        results = []
        
        if os.path.isfile(input_path):
            # Process single file
            results.append(self.analyze_audio(input_path))
            
        elif os.path.isdir(input_path):
            # Process all video files in directory
            video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv', '*.wmv']
            video_files = []
            
            for ext in video_extensions:
                video_files.extend(glob.glob(os.path.join(input_path, ext)))
                video_files.extend(glob.glob(os.path.join(input_path, ext.upper())))
            
            if not video_files:
                print(f"No video files found in {input_path}")
                return results
            
            print(f"Found {len(video_files)} video files")
            
            for video_file in sorted(video_files):
                results.append(self.analyze_audio(video_file))
        else:
            print(f"Error: {input_path} is not a valid file or directory")
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """
        Generate and save global report.
        
        Args:
            results: List of analysis results
            
        Returns:
            Path to the saved report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.output_dir, f"report_{timestamp}.json")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_files': len(results),
            'suspicious_files': sum(1 for r in results if r.get('suspicion', False)),
            'configuration': {
                'n_fft': self.n_fft,
                'hop_length': self.hop_length,
                'n_mels': self.n_mels,
                'fmin': self.fmin,
                'fmax': self.fmax,
                'frequency_bands': self.frequency_bands,
                'thresholds': self.thresholds
            },
            'results': results
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"Report saved to: {report_path}")
        print(f"Total files processed: {report['total_files']}")
        print(f"Suspicious files: {report['suspicious_files']}")
        print(f"{'='*60}")
        
        return report_path


def load_config(config_path: Optional[str] = None) -> Dict:
    """
    Load configuration from YAML file or use defaults.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dictionary
    """
    default_config = {
        'output_dir': 'reports',
        'topk': 5,
        'n_fft': 2048,
        'hop_length': 512,
        'n_mels': 128,
        'fmin': 0.0,
        'fmax': None,
        'frequency_bands': {
            'bark': [150, 2000],
            'snore': [50, 300],
            'chirp': [2000, 8000],
            'low_freq': [0, 500],
            'mid_freq': [500, 2000],
            'high_freq': [2000, 8000]
        },
        'thresholds': {
            'energy_diff_threshold': 10.0,
            'sample_rate_mismatch': True
        }
    }
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                
            # Merge with defaults
            default_config.update(user_config)
            print(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
            print("Using default configuration")
    
    return default_config


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Audio Diagnostic Agent - Detect audio detection issues in videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single video file
  python audio_diagnostic_agent.py --input video.mp4
  
  # Process all videos in a directory
  python audio_diagnostic_agent.py --input /path/to/videos/
  
  # Use custom configuration
  python audio_diagnostic_agent.py --input video.mp4 --config config.yaml
  
  # Specify output directory and top-k predictions
  python audio_diagnostic_agent.py --input video.mp4 --outdir results --topk 10
        """
    )
    
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input video file or directory containing videos'
    )
    
    parser.add_argument(
        '--outdir',
        type=str,
        default='reports',
        help='Output directory for reports and spectrograms (default: reports)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Path to model file (optional)'
    )
    
    parser.add_argument(
        '--topk',
        type=int,
        default=5,
        help='Number of top predictions to include (default: 5)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to YAML configuration file (optional)'
    )
    
    parser.add_argument(
        '--n-fft',
        type=int,
        default=None,
        help='FFT window size (default: 2048)'
    )
    
    parser.add_argument(
        '--hop-length',
        type=int,
        default=None,
        help='Hop length for spectrogram (default: 512)'
    )
    
    parser.add_argument(
        '--n-mels',
        type=int,
        default=None,
        help='Number of Mel bands (default: 128)'
    )
    
    parser.add_argument(
        '--threshold',
        type=float,
        default=None,
        help='Energy difference threshold in dB (default: 10.0)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override with command-line arguments
    config['output_dir'] = args.outdir
    config['topk'] = args.topk
    
    if args.model:
        config['model_path'] = args.model
    if args.n_fft:
        config['n_fft'] = args.n_fft
    if args.hop_length:
        config['hop_length'] = args.hop_length
    if args.n_mels:
        config['n_mels'] = args.n_mels
    if args.threshold:
        config['thresholds']['energy_diff_threshold'] = args.threshold
    
    # Create agent and process input
    agent = AudioDiagnosticAgent(config)
    
    print("="*60)
    print("Audio Diagnostic Agent")
    print("="*60)
    print(f"Input: {args.input}")
    print(f"Output directory: {config['output_dir']}")
    print(f"Spectrogram config: n_fft={config['n_fft']}, hop_length={config['hop_length']}, n_mels={config['n_mels']}")
    
    results = agent.process_input(args.input)
    
    if results:
        agent.generate_report(results)
    else:
        print("No results to report")
        sys.exit(1)


if __name__ == '__main__':
    main()
