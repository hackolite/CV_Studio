import subprocess

def is_valid_video(filepath):
    try:
        subprocess.run([
            "ffprobe", "-v", "quiet",
            "-show_format", "-show_streams",
            "-print_format", "json",
            filepath
        ], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
