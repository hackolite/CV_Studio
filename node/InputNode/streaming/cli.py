import sys
import glob
from .extractor import get_live_stream_url
from .segmenter import download_segments
from .utils import is_valid_video

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m ytlive_dl.cli <URL_YOUTUBE_LIVE> [segment_time]")
        return

    url = sys.argv[1]
    segment_time = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    manifest_url = get_live_stream_url(url)
    if manifest_url:
        download_segments(manifest_url, segment_time=segment_time)

        files = sorted(glob.glob("chunk_*.mp4"))
        if files:
            print("🔍 Vérification du premier fichier :", files[0])
            valid = is_valid_video(files[0])
            if valid:
                print("✅ Fichier valide.")
            else:
                print("❌ Fichier corrompu.")


if __name__ == "__main__":
    main()
