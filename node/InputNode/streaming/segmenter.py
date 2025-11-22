import subprocess
import os
from .downloader import fallback_recording
from .utils import is_valid_video

def download_segments(manifest_url, output_pattern="chunk_%03d.mp4", segment_time=30):
    if not manifest_url:
        print("🚫 URL de stream invalide.")
        return

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "info",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", manifest_url,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "25",
        "-c:a", "pcm_s16le",  # WAV codec for efficient spectrogram conversion
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-reset_timestamps", "1",
        output_pattern
    ]

    print("🚀 Lancement de ffmpeg en mode segmenté...")
    try:
        subprocess.run(cmd, check=True)
        print("✅ Téléchargement terminé")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur ffmpeg : {e}")
        fallback_recording(manifest_url, output_pattern, segment_time)
