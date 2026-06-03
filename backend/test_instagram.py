import yt_dlp

url = "https://www.instagram.com/reel/DYs2sTkgJzN/"

ydl_opts = {
    "quiet": False,
    "skip_download": True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)

print(info.keys())
print(info.get("uploader"))
print(info.get("description"))
print(info.get("like_count"))