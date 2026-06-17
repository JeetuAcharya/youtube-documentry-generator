import os
import requests
import json
import asyncio
import datetime
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip, ImageClip
import moviepy.video.fx.all as vfx
import moviepy.audio.fx.all as afx

# --- SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "Assets", "Videos")
AUDIO_DIR = os.path.join(BASE_DIR, "Assets", "Audio")
HUD_DIR = os.path.join(BASE_DIR, "Assets", "HUDs")
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(HUD_DIR, exist_ok=True)

import hud_generator

# API Keys (Loaded securely from environment variables)
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "YOUR_PEXELS_KEY")
NVIDIA_NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "YOUR_NVIDIA_KEY")

def search_pexels_video(query):
    if PEXELS_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please put your Pexels API key in documentary_engine.py!")
        return None
        
    print(f"Searching Pexels for: {query}...")
    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {"query": query, "per_page": 1, "orientation": "landscape"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("videos"):
            video_files = data["videos"][0].get("video_files", [])
            # Get HD video (1920x1080) if possible
            hd_video = next((f for f in video_files if f.get("quality") == "hd" and f.get("width", 0) >= 1920), video_files[0] if video_files else None)
            if hd_video:
                return hd_video.get("link")
    except Exception as e:
        print(f"Error fetching from Pexels: {e}")
    return None

def download_video(url, filename):
    import time
    filepath = os.path.join(VIDEOS_DIR, filename)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    for attempt in range(3):
        print(f"Downloading video to {filepath} (Attempt {attempt+1}/3)...")
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=20)
            r.raise_for_status()
            with open(filepath, 'wb') as out_file:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        out_file.write(chunk)
            return filepath
        except Exception as e:
            print(f"Error downloading video: {e}")
            if attempt < 2:
                print("Waiting 10 seconds before trying again...")
                time.sleep(10)
    return filepath

async def generate_tts(text, filename, voice="en-US-ChristopherNeural"):
    filepath = os.path.join(AUDIO_DIR, filename)
    print(f"Generating Voiceover [{voice}]: {text[:30]}...")
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)
        return filepath
    except Exception as e:
        print(f"TTS failed with voice {voice}: {e}. Trying fallback...")
        fallback = "en-GB-RyanNeural"
        communicate = edge_tts.Communicate(text, fallback)
        await communicate.save(filepath)
        return filepath

def get_trending_topics():
    print("Fetching today's trending topics from Wikipedia...")
    # Get yesterday's date to ensure data is fully populated
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    date_str = yesterday.strftime("%Y/%m/%d")
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia.org/all-access/{date_str}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        articles = data.get("items", [])[0].get("articles", [])
        
        topics = []
        # Filter out Wikipedia meta pages
        exclude = ["Main_Page", "Special:Search", "Wikipedia:", "File:"]
        for item in articles:
            title = item.get("article", "")
            if title and not any(title.startswith(x) for x in exclude):
                clean_title = title.replace("_", " ")
                topics.append(clean_title)
                if len(topics) >= 5:
                    break
                    
        print(f"Found trending topics: {', '.join(topics)}")
        return topics if topics else ["Artificial Intelligence", "Space Exploration"]
    except Exception as e:
        print(f"Error fetching trends: {e}")
        return ["Artificial Intelligence", "Lost Civilizations", "Space Exploration", "Unsolved Mysteries"]

def generate_script(topic):
    print(f"Generating unique documentary script incorporating trend: {topic}...")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {NVIDIA_NIM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    prompt = (
        "You are a professional documentary scriptwriter. "
        "Invent a completely unique, highly obscure, never-before-heard topic for a documentary. "
        "The genre must be one of: Horror, Lost History, or Mythology. "
        f"CRITICAL VIRALITY RULE: To make it relevant today, you MUST subtly tie the historical/mythological topic to this currently trending topic: {topic}. "
        "Write a script that will translate to a 15-minute video. This requires a very long script, around 20 to 30 scenes. "
        "Output ONLY a valid JSON object with EXACTLY two keys:\n"
        "1. 'description': A detailed, highly engaging 2-to-3 paragraph English YouTube description for this documentary.\n"
        "2. 'scenes': An array of scene objects. Each object must have exactly two keys:\n"
        "   - 'query' (a short 1-3 word English search term for Pexels video search representing the visual, e.g. 'dark forest')\n"
        "   - 'text' (the dramatic English voiceover script for that scene, roughly 3-5 sentences)\n"
        "Do not include any other text, markdown formatting, or explanations outside the JSON object."
    )
    
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Clean up potential markdown formatting
        content = content.strip()
        if content.startswith("```json"): content = content[7:]
        elif content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        
        data = json.loads(content.strip())
        scenes = data.get("scenes", [])
        desc = data.get("description", f"What is the real secret behind {topic}? Watch to find out.")
        print(f"Successfully generated script with {len(scenes)} scenes!")
        return scenes, desc
    except Exception as e:
        print(f"Error generating script: {e}")
        return [{"query": "dark ocean", "text": "The script generation failed, but the depths remain dark."}], "Failed to generate description."

async def build_documentary():
    topics = get_trending_topics()
    main_topic = topics[0] if topics else "UNSOLVED MYSTERIES"
    scenes, long_description = generate_script(main_topic)
    if not scenes: return
    
    video_clips = []
    
    for i, scene in enumerate(scenes):
        print(f"\n--- Processing Scene {i+1} ---")
        
        # 1. Download Video
        video_url = search_pexels_video(scene["query"])
        if not video_url:
            print("Aborting. No video found or API key missing.")
            return
            
        vid_path = download_video(video_url, f"scene_{i}.mp4")
        
        # 2. Generate Audio
        aud_path = await generate_tts(scene["text"], f"audio_{i}.mp3")
        
        # 3. Process Clip
        vid_clip = VideoFileClip(vid_path)
        aud_clip = AudioFileClip(aud_path)
        
        # Professional Editing: Resize and Center Crop to 1920x1080
        clip_ratio = vid_clip.w / vid_clip.h
        target_ratio = 1920 / 1080
        
        if clip_ratio > target_ratio:
            vid_clip = vid_clip.fx(vfx.resize, height=1080)
        else:
            vid_clip = vid_clip.fx(vfx.resize, width=1920)
            
        vid_clip = vid_clip.fx(vfx.crop, x_center=vid_clip.w/2, y_center=vid_clip.h/2, width=1920, height=1080)
        
        # Loop or Trim video to match audio length
        if vid_clip.duration < aud_clip.duration:
            vid_clip = vid_clip.fx(vfx.loop, duration=aud_clip.duration)
        else:
            vid_clip = vid_clip.subclip(0, aud_clip.duration)
            
        # Add cinematic dip-to-black transitions
        vid_clip = vid_clip.fx(vfx.fadein, 0.5).fx(vfx.fadeout, 0.5)
        
        # Cinematic Color Grading (Netflix / NatGeo style)
        # Darken by 15% and increase contrast
        vid_clip = vid_clip.fx(vfx.colorx, 0.85)
        vid_clip = vid_clip.fx(vfx.lum_contrast, lum=0, contrast=0.2)
        
        # Dynamically Generate HUD Overlay
        if i == 0:
            hud_array = hud_generator.generate_intro_hud(main_topic)
        elif i == len(scenes) - 1:
            hud_array = hud_generator.generate_outro_hud(main_topic)
        else:
            # Rotate between different HUD styles to keep the video dynamic and engaging
            if i % 4 == 0:
                hud_array = hud_generator.generate_focus_hud(main_topic)
            elif i % 3 == 0:
                hud_array = hud_generator.generate_highlight_hud(main_topic)
            else:
                hud_array = hud_generator.generate_main_hud(main_topic, i, len(scenes))
            
        print("Overlaying dynamic python HUD...")
        hud_clip = ImageClip(hud_array).set_duration(vid_clip.duration).resize(vid_clip.size)
        vid_clip = CompositeVideoClip([vid_clip, hud_clip])
        
        vid_clip = vid_clip.set_audio(aud_clip)
        video_clips.append(vid_clip)
        
    print("\nStitching final documentary...")
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # 4. Add Background Music
    bgm_path = os.path.join(AUDIO_DIR, "bgm.mp3")
    if os.path.exists(bgm_path):
        print("Mixing in background music...")
        bgm_clip = AudioFileClip(bgm_path)
        if bgm_clip.duration < final_video.duration:
            bgm_clip = bgm_clip.fx(afx.audio_loop, duration=final_video.duration)
        else:
            bgm_clip = bgm_clip.subclip(0, final_video.duration)
        
        # Lower BGM volume to 10%
        bgm_clip = bgm_clip.fx(afx.volumex, 0.1)
        final_audio = CompositeAudioClip([final_video.audio, bgm_clip])
        final_video = final_video.set_audio(final_audio)
    else:
        print("No bgm.mp3 found in Assets/Audio, skipping background music.")

    output_path = os.path.join(BASE_DIR, "final_documentary.mp4")
    
    # Heavily optimized for GitHub Actions (2-core cloud servers)
    # ultrafast preset reduces render time by ~3x to 5x.
    final_video.write_videofile(
        output_path, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac", 
        preset="ultrafast", 
        threads=4
    )
    print(f"SUCCESS! Documentary saved to {output_path}")

    # 5. UPLOAD PHASE
    import uploader
    
    # Generate catchy, small, high-retention title and description with 4 hashtags
    clean_topic = main_topic.replace(" ", "")
    title = f"The Terrifying Truth of {main_topic.title()} 🚨"
    final_description = f"{long_description}\n\n#{clean_topic} #documentary #mystery #history"
    
    print("\n--- Starting Upload Phase ---")
    uploader.upload_to_youtube(output_path, title, final_description, privacy_status="public")
    uploader.upload_to_facebook_video(output_path, title, final_description)
    
    # 6. CLEANUP PHASE
    print("\n--- Starting Cleanup Phase ---")
    # Release memory locks from moviepy to allow file deletion
    final_video.close()
    
    import time
    time.sleep(2) # Brief wait to ensure OS releases file locks
    
    print("Deleting temporary video and audio clips to save space...")
    for f in os.listdir(VIDEOS_DIR):
        f_path = os.path.join(VIDEOS_DIR, f)
        if os.path.isfile(f_path) and f.endswith(".mp4"):
            try: os.remove(f_path)
            except Exception as e: print(f"Warning: could not delete {f_path}: {e}")
            
    for f in os.listdir(AUDIO_DIR):
        f_path = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(f_path) and f.endswith(".mp3") and f != "bgm.mp3":
            try: os.remove(f_path)
            except Exception as e: print(f"Warning: could not delete {f_path}: {e}")
            
    print("Deleting final rendered video...")
    try: 
        if os.path.exists(output_path):
            os.remove(output_path)
    except Exception as e: 
        print(f"Warning: could not delete {output_path}: {e}")
            
    print("Cleanup Complete! System is fully clean for GitHub Actions.")

if __name__ == "__main__":
    asyncio.run(build_documentary())
