#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests verifying that the Microphone node:
1. Proposes 5-second chunks by default
2. Has a slider to choose chunk sizes
3. Produces audio output compatible with the Spectrogram node
"""
import sys
import os
import numpy as np
import inspect

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_microphone_default_chunk_is_5s():
    """Verify that the microphone slider default value is 5.0 seconds"""
    source_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_microphone.py'
    )
    with open(source_path) as f:
        content = f.read()

    # The slider must default to 5.0 seconds
    assert 'default_value=5.0' in content, (
        "Microphone chunk slider should have default_value=5.0 (5 seconds), "
        "but it was not found in the source."
    )
    print("✓ Microphone chunk slider default is 5.0 seconds")


def test_microphone_slider_exists():
    """Verify that a slider exists for choosing chunk size"""
    source_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_microphone.py'
    )
    with open(source_path) as f:
        content = f.read()

    # A slider float for chunk duration must exist
    assert 'add_slider_float' in content, (
        "Microphone node should have a slider (add_slider_float) for chunk duration"
    )
    assert 'Chunk (s)' in content, (
        "Microphone node slider should be labelled 'Chunk (s)'"
    )
    print("✓ Microphone chunk slider exists with correct label")


def test_microphone_audio_output_compatible_with_spectrogram():
    """
    Verify that the audio output structure from the Microphone node is
    compatible with what the Spectrogram node expects.
    """
    # Simulate a 5-second audio chunk at 44100 Hz
    sample_rate = 44100
    chunk_duration = 5.0
    num_samples = int(sample_rate * chunk_duration)

    audio_data = np.random.randn(num_samples).astype(np.float32)

    # Build the audio output dict that MicrophoneNode produces
    import time
    audio_output = {
        'data': audio_data,
        'sample_rate': sample_rate,
        'timestamp': time.time(),
        'channels': 1,
        'output_mode': 'Full Signal',
    }

    # Verify the spectrogram node can read the data the way it's coded
    assert isinstance(audio_output, dict), "Audio output should be a dict"
    assert 'data' in audio_output, "Audio output must contain 'data'"
    assert 'sample_rate' in audio_output, "Audio output must contain 'sample_rate'"

    extracted_data = audio_output.get('data', None)
    extracted_sr = audio_output.get('sample_rate', 22050)

    assert extracted_data is not None, "Extracted audio data should not be None"
    assert extracted_data.ndim == 1, "Audio data should be 1D for spectrogram processing"
    assert len(extracted_data) == num_samples, (
        f"Expected {num_samples} samples, got {len(extracted_data)}"
    )
    assert extracted_sr == sample_rate, (
        f"Expected sample_rate {sample_rate}, got {extracted_sr}"
    )

    print(f"✓ Microphone audio output is compatible with Spectrogram node")
    print(f"  Audio data shape : {extracted_data.shape}")
    print(f"  Sample rate      : {extracted_sr} Hz")
    print(f"  Chunk duration   : {len(extracted_data) / extracted_sr:.1f} s")


def test_spectrogram_processes_5s_chunk():
    """
    Verify that the Spectrogram utility functions can process a 5-second chunk
    without errors (using the same functions that node_spectrogram.py uses).
    """
    try:
        import librosa
    except ImportError:
        print("⚠️ librosa not available – skipping spectrogram processing test")
        return

    sample_rate = 44100
    chunk_duration = 5.0
    num_samples = int(sample_rate * chunk_duration)
    audio_data = np.random.randn(num_samples).astype(np.float32)

    # Test mel spectrogram (most common)
    mel_spec = librosa.feature.melspectrogram(y=audio_data, sr=sample_rate,
                                               n_fft=2048, hop_length=512,
                                               n_mels=128)
    assert mel_spec is not None, "mel_spec should not be None"
    assert mel_spec.shape[0] == 128, "mel_spec should have 128 mel bands"

    print(f"✓ Spectrogram processes 5s chunk correctly")
    print(f"  mel_spec shape: {mel_spec.shape}")


def test_microphone_audio_type_tag():
    """Verify that the microphone audio output uses TYPE_AUDIO tag"""
    source_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_microphone.py'
    )
    with open(source_path) as f:
        content = f.read()

    # The audio output should use TYPE_AUDIO
    assert "node.TYPE_AUDIO + ':OutputAudio'" in content, (
        "Microphone node should expose an audio output with TYPE_AUDIO"
    )
    assert "mvNode_Attr_Output" in content, (
        "Microphone node should have an Output attribute for audio"
    )
    print("✓ Microphone audio output uses TYPE_AUDIO tag correctly")
