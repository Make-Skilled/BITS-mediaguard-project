import yt_dlp
import subprocess
import os

# URL of the video to download
video_url = 'https://www.youtube.com/watch?v=_oRB1hymO14'  # Replace with your video URL

# Text to overlay on the video
watermark_text = 'Your Watermark Text Here'  # Replace with your text

# Download the video
def download_video(url):
    ydl_opts = {
        'format': 'worst',  # Download the lowest available quality
        'outtmpl': 'downloaded_video.%(ext)s',  # Output filename template
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        return f"downloaded_video.{result['ext']}"

# Add text watermark to the downloaded video
def add_text_watermark(input_video, text, output_video):
    command = [
        'ffmpeg',
        '-i', input_video,  # Input video
        '-vf', f"drawtext=text='{text}':fontcolor=white:fontsize=24:x=10:y=10",  # Overlay text at position (10, 10)
        '-c:a', 'copy',  # Copy the audio codec without re-encoding
        output_video      # Output file name
    ]
    
    result = subprocess.run(command, stderr=subprocess.PIPE)
    print(result.stderr.decode())  # Print any FFmpeg errors

# Execute the process
downloaded_video = download_video(video_url)
print(f"Downloaded video: {downloaded_video}")

output_video = 'video_with_text_watermark.mp4'
add_text_watermark(downloaded_video, watermark_text, output_video)
print(f"Watermarked video saved as: {output_video}")

# Optionally, clean up the original downloaded video
os.remove(downloaded_video)
