import subprocess
import os

def fallback_recording(manifest_url, output_pattern, segment_time):
    temp_file = "temp_recording.mp4"
    print("📼 Enregistrement complet temporaire...")

    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "info",
            "-i", manifest_url,
            "-c", "copy",
            "-t", "300",  # 5 minutes
            temp_file
        ], check=True)

        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_file,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(segment_time),
            "-reset_timestamps", "1",
            output_pattern
        ], check=True)

        print("✅ Segmentation terminée.")
        os.remove(temp_file)

    except Exception as e:
        print(f"❌ Fallback échoué : {e}")
