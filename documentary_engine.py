import os
import requests
import json
import asyncio
import datetime
import random
import subprocess

# Fix for MoviePy compatibility with Pillow >= 10.0.0
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

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
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
NVIDIA_NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "")

def search_pexels_video(query):
    if PEXELS_API_KEY == "YOUR_PEXELS_KEY":
        print("ERROR: Please put your Pexels API key in documentary_engine.py or set the environment variable!")
        return None
        
    print(f"Searching Pexels for: {query}...")
    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "Mozilla/5.0"
    }
    params = {"query": query, "per_page": 1, "orientation": "landscape"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("videos"):
            video_files = data["videos"][0].get("video_files", [])
            hd_video = next((f for f in video_files if f.get("quality") == "hd" and f.get("width", 0) >= 1920), video_files[0] if video_files else None)
            if hd_video:
                return hd_video.get("link")
    except Exception as e:
        print(f"Error fetching from Pexels: {e}")
    return None

def download_video(url, filename):
    import time
    filepath = os.path.join(VIDEOS_DIR, filename)
    headers = {"User-Agent": "Mozilla/5.0"}
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
                time.sleep(10)
    return filepath

NVIDIA_NIM_MAGPIE_API_KEY = os.environ.get("NVIDIA_NIM_MAGPIE_API_KEY", "")
NVIDIA_NIM_CHATTERBOX_API_KEY = os.environ.get("NVIDIA_NIM_CHATTERBOX_API_KEY", "")

async def generate_tts(text, filename):
    filepath = os.path.join(AUDIO_DIR, filename)
    print("Generating Voiceover via Edge-TTS...")
    
    import edge_tts
    for attempt in range(3):
        try:
            # We slow it down slightly and drop the pitch for a dramatic documentary tone
            communicate = edge_tts.Communicate(
                text, 
                "en-US-ChristopherNeural", 
                rate="-5%",
                pitch="-5Hz"
            )
            raw_filepath = filepath.replace(".mp3", "_raw.mp3")
            timing_filepath = filepath.replace(".mp3", "_timing.json")
            
            word_boundaries = []
            with open(raw_filepath, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        # offset and duration are in 100-nanosecond units, convert to seconds
                        word_boundaries.append({
                            "start": chunk["offset"] / 10_000_000,
                            "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                            "text": chunk["text"]
                        })
                        
            with open(timing_filepath, "w", encoding="utf-8") as f:
                json.dump(word_boundaries, f, ensure_ascii=False)
            
            if os.path.exists(raw_filepath) and os.path.getsize(raw_filepath) > 0:
                print("Applying cinematic audio filters (Bass Boost, Reverb, Compression)...")
                # Transform the flat AI voice into a 'Voice of God' studio recording using FFmpeg
                # 1. Bass boost (+7dB at 100Hz) for deep radio resonance
                # 2. Treble boost (+3dB at 6000Hz) for crisp articulation
                # 3. Echo (subtle 20ms delay) for studio room acoustics
                # 4. Compressor to level out the volume perfectly
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", raw_filepath,
                    "-af", "bass=g=7:f=100,treble=g=3:f=6000,aecho=0.8:0.8:20:0.2,acompressor=ratio=4",
                    filepath
                ]
                subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Clean up the raw file
                try:
                    os.remove(raw_filepath)
                except:
                    pass
                
                return filepath
            else:
                print(f"Edge-TTS returned empty file on attempt {attempt+1}")
        except Exception as e:
            print(f"Edge-TTS failed on attempt {attempt+1}: {e}")
            
        await asyncio.sleep(2)
        
    return None

def get_trending_topics():
    print("Fetching today's trending topics from Google Trends...")
    url = "https://trends.google.com/trending/rss?geo=IN"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        topics = []
        for item in root.findall('.//item'):
            title = item.find('title')
            if title is not None and title.text:
                topics.append(title.text)
                if len(topics) >= 5:
                    break
                    
        if topics:
            print(f"Found Google trending topics: {', '.join(topics)}")
            return topics
        else:
            raise Exception("No topics found in RSS feed")
    except Exception as e:
        print(f"Error fetching Google Trends: {e}")
        print("Fallback: Letting AI invent a random topic...")
        return []

def generate_script(topic):
    print(f"Generating unique documentary script via Nvidia NIM API (meta/llama-3.1-8b-instruct)...")
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    nim_key = os.environ.get("NVIDIA_NIM_API_KEY", "")
    if not nim_key:
        print("Warning: NVIDIA_NIM_API_KEY not found in environment. Attempting to proceed, but API call may fail.")
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {nim_key}",
        "Accept": "application/json"
    }
    
    genre = random.choice(["Horror", "Lost History", "Universe", "Science", "Finance"])

    topic_instruction = f"Your task is to write a highly engaging, 15-minute documentary script about a completely unique, fascinating, and obscure topic of your own choosing within the {genre} genre."

    prompt = (
        "You are a professional documentary scriptwriter. "
        f"{topic_instruction} "
        f"CRITICAL RULE: You MUST write this documentary strictly in the genre of: {genre}. "
        "Do NOT mix genres together! Keep the tone completely consistent and separated. "
        "Write a detailed script, around 5 to 8 scenes. "
        "Output ONLY a valid JSON object with EXACTLY three keys:\n"
        "1. 'tags': An array of 20 highly optimized SEO tags for YouTube search (e.g. ['documentary', 'unsolved mystery', 'history']).\n"
        "2. 'description': A detailed, highly engaging 2-to-3 paragraph English YouTube description for this documentary. (CRITICAL: Use '\\n' for newlines, do NOT press enter/use actual line breaks inside the string!)\n"
        "3. 'scenes': An array of scene objects. Each object must have exactly two keys:\n"
        "   - 'queries' (an array of 3 distinct 1-3 word English search terms for Pexels video search representing different camera angles/visuals for the scene, e.g. ['dark forest', 'full moon', 'creepy shadows'])\n"
        "   - 'text' (The dramatic voiceover script for that scene in PERFECT, high-impact English. Make it extremely suspenseful and engaging. DO NOT just state boring facts. You MUST talk directly to the audience, ask them mysterious questions, and use cliffhangers! e.g., 'There is a legend in this dark forest... but do you guys know the terrifying truth behind it?').\n"
        "CRITICAL TTS INSTRUCTION: You MUST use heavy punctuation! Use commas (,), ellipses (...), and periods (.) frequently to force dramatic pauses. This is for an AI voiceover, so punctuation acts as 'breathing room' to make it sound realistic.\n"
        "CRITICAL JSON INSTRUCTION: Do NOT use double quotes (\") anywhere inside your text fields! If you need to quote a word or phrase, use single quotes (') instead. Unescaped double quotes will corrupt the JSON format.\n"
        "Do not include any other text, markdown formatting, or explanations outside the JSON object."
    )
    
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
        else:
            print(f"Unexpected NIM Response format: {result}")
            return [], "", []
        
        import re
        
        # Clean up potential markdown formatting
        content = content.strip()
        if content.startswith("```json"): content = content[7:]
        elif content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        
        # Fix trailing commas (very common LLM mistake)
        content = re.sub(r',\s*([\]}])', r'\1', content)
        
        # strict=False allows literal unescaped newlines/control characters in the JSON
        data = json.loads(content.strip(), strict=False)
        scenes = data.get("scenes", [])
        desc = data.get("description", f"What is the real secret behind {topic}? Watch to find out.")
        if isinstance(desc, list):
            desc = "\n\n".join(desc)
            
        tags = data.get("tags", ["documentary", "mystery", "history"])
        print(f"Successfully generated script with {len(scenes)} scenes and {len(tags)} tags!")
        return scenes, desc, tags
    except Exception as e:
        print(f"Error generating script: {e}")
        return [{"queries": ["dark ocean", "deep sea", "storm"], "text": "The script generation failed, but the depths remain dark."}], "Failed to generate description.", ["error", "documentary"]

def create_subtitle_clip(text, start, end, video_size=(1920, 1080)):
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    
    img = Image.new('RGBA', video_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_path = os.path.join(BASE_DIR, "Roboto-Medium.ttf")
    if not os.path.exists(font_path):
        import urllib.request
        try:
            urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Medium.ttf", font_path)
        except:
            pass
            
    try:
        font = ImageFont.truetype(font_path, 110) # Big bold text
    except IOError:
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (video_size[0] - text_w) / 2
    y = video_size[1] - text_h - 220 # Position at bottom
    
    # Draw thick black outline for visibility on bright/dark backgrounds
    outline_color = (0, 0, 0, 255)
    outline_width = 7
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx*dx + dy*dy <= outline_width*outline_width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
                
    # Draw white text
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    img_np = np.array(img)
    clip = ImageClip(img_np).set_start(start).set_end(end)
    return clip

async def build_documentary():
    # We no longer use Google Trends. We let the AI invent a fascinating topic based on the genres.
    scenes, long_description, tags = generate_script(topic=None)
    
    # Use the first generated tag as the title fallback
    main_topic = tags[0].title() if tags else "Unsolved Mystery"
    if not scenes: return
    
    video_clips = []
    
    for i, scene in enumerate(scenes):
        print(f"\n--- Processing Scene {i+1} ---")
        
        # 1. Download Videos from Pexels (Multiple clips per scene)
        vid_paths = []
        queries = scene.get("queries", ["dark forest"])
        for j, query in enumerate(queries):
            video_url = search_pexels_video(query)
            if video_url:
                v_path = download_video(video_url, f"scene_{i}_clip_{j}.mp4")
                if v_path: vid_paths.append(v_path)
                
        if not vid_paths:
            print(f"Warning: No videos generated for scene {i+1}, skipping scene.")
            continue
            
        # 2. Generate Audio
        aud_path = await generate_tts(scene["text"], f"audio_{i}.mp3")
        if not aud_path:
            print(f"Failed to generate audio for scene {i+1}, skipping.")
            continue
        aud_clip = AudioFileClip(aud_path)
        # Increase TTS volume slightly by 30% to make the voice punchier
        aud_clip = aud_clip.fx(afx.volumex, 1.3)
        scene_duration = aud_clip.duration
        
        # 3. Process Clips (Slice them dynamically)
        subclips = []
        clip_duration = scene_duration / len(vid_paths)
        
        for j, v_path in enumerate(vid_paths):
            vc = VideoFileClip(v_path)
            
            # Professional Editing: Resize and Center Crop to 1920x1080
            clip_ratio = vc.w / vc.h
            target_ratio = 1920 / 1080
            
            if clip_ratio > target_ratio: vc = vc.fx(vfx.resize, height=1080)
            else: vc = vc.fx(vfx.resize, width=1920)
                
            vc = vc.fx(vfx.crop, x_center=vc.w/2, y_center=vc.h/2, width=1920, height=1080)
            
            # Loop or Trim
            if vc.duration < clip_duration:
                vc = vc.fx(vfx.loop, duration=clip_duration)
            else:
                vc = vc.subclip(0, clip_duration)
                
            # Add subtle crossfades between rapid-b-roll clips
            if j > 0: vc = vc.fx(vfx.fadein, 0.3)
            if j < len(vid_paths) - 1: vc = vc.fx(vfx.fadeout, 0.3)
                
            vc = vc.fx(vfx.colorx, 0.85).fx(vfx.lum_contrast, lum=0, contrast=0.2)
            subclips.append(vc)
            
        # Stitch subclips for this scene
        scene_vid_clip = concatenate_videoclips(subclips, method="compose")
        
        if scene_vid_clip.duration > aud_clip.duration:
            scene_vid_clip = scene_vid_clip.subclip(0, aud_clip.duration)
            
        # Dip to black at the ends of the whole scene
        scene_vid_clip = scene_vid_clip.fx(vfx.fadein, 0.5).fx(vfx.fadeout, 0.5)
        
        # Dynamically Generate HUD Overlay
        if i == 0: hud_array = hud_generator.generate_intro_hud(main_topic)
        elif i == len(scenes) - 1: hud_array = hud_generator.generate_outro_hud(main_topic)
        else:
            if i % 4 == 0: hud_array = hud_generator.generate_focus_hud(main_topic)
            elif i % 3 == 0: hud_array = hud_generator.generate_highlight_hud(main_topic)
            else: hud_array = hud_generator.generate_main_hud(main_topic, i, len(scenes))
            
        print("Overlaying dynamic python HUD and Subtitles...")
        hud_clip = ImageClip(hud_array).set_duration(scene_vid_clip.duration).resize(scene_vid_clip.size)
        
        # Load Subtitles
        timing_path = aud_path.replace(".mp3", "_timing.json")
        subtitle_clips = []
        if os.path.exists(timing_path):
            try:
                with open(timing_path, "r", encoding="utf-8") as f:
                    words = json.load(f)
                
                chunk = []
                chunk_start = 0
                for w in words:
                    if not chunk: chunk_start = w["start"]
                    chunk.append(w["text"])
                    # Group every 3 words or end of sentence to make it readable
                    if len(chunk) >= 3 or w["text"].endswith(('.', ',', '?', '!')):
                        chunk_text = " ".join(chunk)
                        chunk_end = w["end"]
                        # Extend slightly to prevent flickering, capped at scene duration
                        chunk_end = min(chunk_end + 0.1, scene_vid_clip.duration)
                        if chunk_start < scene_vid_clip.duration:
                            sub_clip = create_subtitle_clip(chunk_text, chunk_start, chunk_end, scene_vid_clip.size)
                            subtitle_clips.append(sub_clip)
                        chunk = []
                        
                # Cleanup timing file
                try: os.remove(timing_path)
                except: pass
            except Exception as e:
                print(f"Failed to generate subtitles: {e}")
                
        composite_layers = [scene_vid_clip, hud_clip] + subtitle_clips
        scene_vid_clip = CompositeVideoClip(composite_layers)
        
        scene_vid_clip = scene_vid_clip.set_audio(aud_clip)
        video_clips.append(scene_vid_clip)
        
    print("\nStitching final documentary...")
    if not video_clips:
        print("CRITICAL ERROR: No video clips were generated (Check your internet connection/API keys). Cannot stitch documentary.")
        return
        
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
    video_id = uploader.upload_to_youtube(output_path, title, final_description, tags=tags, privacy_status="public")
    if video_id:
        uploader.pin_comment(video_id, "What do you think is the real truth behind this mystery? Let me know below! 👇")
        
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
            
    # We will NOT delete the final rendered video so it can be viewed locally.
            
    print("Cleanup Complete! System is fully clean for GitHub Actions.")

if __name__ == "__main__":
    asyncio.run(build_documentary())
