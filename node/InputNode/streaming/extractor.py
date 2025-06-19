import yt_dlp

def get_live_stream_url(youtube_url):
    ydl_opts = {
        'quiet': False,
        'skip_download': True,
        'format': 'best[ext=mp4]',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(youtube_url, download=False)
            if not info.get("is_live", False):
                print("⚠️ Ce n'est pas un live actif.")
                return None
            
            formats = info.get("formats", [])
            video_formats = [
                f for f in formats
                if f.get("acodec") != "none" and f.get("vcodec") != "none" and f.get("url")
            ]
            video_formats.sort(key=lambda x: x.get("height", 0), reverse=True)

            if video_formats:
                chosen_format = video_formats[0]
                print(f"🎬 Format sélectionné : {chosen_format['format_id']} - {chosen_format['url']}")
                return chosen_format['url']
            else:
                print("❌ Aucun format valide trouvé.")
                return None

        except Exception as e:
            print(f"❌ Erreur yt_dlp : {e}")
            return None
