from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import requests
import subprocess
import redis
from playwright.sync_api import sync_playwright

# 🚀 FastAPI App
app = FastAPI()

# 🔐 API Key Authentication
API_KEY = "your-secret-api-key"

async def validate_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# 🛠 Redis Cache Setup
cache = redis.Redis(host="localhost", port=6379, decode_responses=True)

def get_cached_video(url):
    return cache.get(url)

def set_cached_video(url, data, ttl=3600):
    cache.set(url, data, ex=ttl)

# 📥 Request Model
class VideoRequest(BaseModel):
    url: str
    remove_watermark: bool = False

# 🎥 Download Function
def fetch_tiktok_video(url, remove_watermark=False):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        video_url = page.eval_on_selector("video", "el => el.src")
        title = page.eval_on_selector("title", "el => el.innerText")
        author = page.eval_on_selector("a[href*='/@']", "el => el.innerText")

        browser.close()

    if remove_watermark:
        video_url = remove_watermark_ffmpeg(video_url)

    return {"video_url": video_url, "title": title, "author": author}

# ❌ Watermark Removal with FFmpeg
def remove_watermark_ffmpeg(video_url):
    output_path = "clean_video.mp4"
    command = [
        "ffmpeg", "-i", video_url, "-vf",
        "delogo=x=10:y=10:w=100:h=50",
        "-c:a", "copy", output_path
    ]
    subprocess.run(command, check=True)
    return output_path

# 🎯 API Endpoint
@app.post("/download")
async def download_video(request: VideoRequest, auth=validate_api_key):
    cached_data = get_cached_video(request.url)
    if cached_data:
        return {"status": "cached", "data": cached_data}

    try:
        video_data = fetch_tiktok_video(request.url, request.remove_watermark)
        set_cached_video(request.url, video_data)
        return {"status": "success", "data": video_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🚀 Run Server (Uncomment if running locally)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
