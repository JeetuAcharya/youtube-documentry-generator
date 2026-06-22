from PIL import Image, ImageDraw, ImageFont
import numpy as np
import datetime
import random

import os
import urllib.request

FONT_URL = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Medium.ttf"
FONT_PATH = "Roboto-Medium.ttf"
FONT_DOWNLOAD_ATTEMPTED = False

def get_font(size):
    global FONT_DOWNLOAD_ATTEMPTED
    if not os.path.exists(FONT_PATH) and not FONT_DOWNLOAD_ATTEMPTED:
        FONT_DOWNLOAD_ATTEMPTED = True
        try:
            print("Downloading standard font for cross-platform consistency...")
            urllib.request.urlretrieve(FONT_URL, FONT_PATH)
        except Exception as e:
            print(f"Warning: Could not download font: {e}")
            
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        # Ultimate fallback
        try:
            return ImageFont.truetype("arial.ttf", size)
        except IOError:
            return ImageFont.load_default()

def draw_corner_brackets(draw, width, height, margin=50, length=40, thickness=2, color="#D4AF37"):
    """Draws cinematic thin corner brackets."""
    # Top Left
    draw.line([(margin, margin), (margin + length, margin)], fill=color, width=thickness)
    draw.line([(margin, margin), (margin, margin + length)], fill=color, width=thickness)
    # Top Right
    draw.line([(width - margin, margin), (width - margin - length, margin)], fill=color, width=thickness)
    draw.line([(width - margin, margin), (width - margin, margin + length)], fill=color, width=thickness)
    # Bottom Left
    draw.line([(margin, height - margin), (margin + length, height - margin)], fill=color, width=thickness)
    draw.line([(margin, height - margin), (margin, height - margin - length)], fill=color, width=thickness)
    # Bottom Right
    draw.line([(width - margin, height - margin), (width - margin - length, height - margin)], fill=color, width=thickness)
    draw.line([(width - margin, height - margin), (width - margin, height - margin - length)], fill=color, width=thickness)

def draw_rec_indicator(draw, margin=50):
    font = get_font(24)
    draw.ellipse([(margin + 10, margin + 15), (margin + 25, margin + 30)], fill="#FF0000")
    draw.text((margin + 35, margin + 10), "REC", font=font, fill="#FFFFFF")

def draw_topic_box(draw, topic, margin=50):
    font_large = get_font(32)
    font_small = get_font(18)
    
    box_x = margin + 10
    box_y = margin + 60
    
    # Draw a thin charcoal gray box with antique gold accent
    draw.rectangle([(box_x, box_y), (box_x + 500, box_y + 80)], outline="#36454F", width=2)
    draw.line([(box_x, box_y), (box_x, box_y + 80)], fill="#D4AF37", width=4)
    
    draw.text((box_x + 15, box_y + 10), "DOCUMENTARY SERIES", font=font_small, fill="#D4AF37")
    draw.text((box_x + 15, box_y + 35), topic.upper(), font=font_large, fill="#FFFFFF")

def draw_audio_meters(draw, width, height, margin=50):
    meter_x = width - margin - 60
    meter_y = height - margin - 150
    
    font = get_font(16)
    draw.text((meter_x, meter_y - 25), "L    R", font=font, fill="#FFFFFF")
    
    # Simulate random audio levels for realism
    l_level = random.randint(5, 15)
    r_level = random.randint(5, 15)
    
    for i in range(20):
        y_pos = meter_y + (i * 6)
        color_l = "#D4AF37" if i > l_level else "#FFFFFF"
        color_r = "#D4AF37" if i > r_level else "#FFFFFF"
        
        draw.line([(meter_x, y_pos), (meter_x + 15, y_pos)], fill=color_l, width=3)
        draw.line([(meter_x + 25, y_pos), (meter_x + 40, y_pos)], fill=color_r, width=3)
        
    draw.text((meter_x - 10, meter_y + 130), "-12.5 dB", font=font, fill="#FFFFFF")

def create_base_hud(width=1920, height=1080):
    # Create a fully transparent image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_corner_brackets(draw, width, height)
    draw_rec_indicator(draw)
    return img, draw

def generate_intro_hud(topic):
    img, draw = create_base_hud()
    draw_topic_box(draw, topic)
    
    width, height = img.size
    
    # Center massive cinematic title
    font_title = get_font(90)
    font_sub = get_font(30)
    
    # Draw centered text (approximate centering, since textbbox can be finicky across PIL versions)
    title_text = topic.upper()
    draw.text((width//2 - len(title_text)*25, height//2 - 50), title_text, font=font_title, fill="#FFFFFF")
    
    sub_text = "A JOURNEY INTO THE UNKNOWN"
    draw.text((width//2 - len(sub_text)*8, height//2 + 60), sub_text, font=font_sub, fill="#D4AF37")
    
    # Map coordinates top right
    font_mono = get_font(20)
    draw.text((width - 250, 60), "4K  |  24 FPS", font=font_mono, fill="#FFFFFF")
    
    return np.array(img)

def generate_main_hud(topic, scene_index, total_scenes):
    img, draw = create_base_hud()
    draw_topic_box(draw, topic)
    draw_audio_meters(draw, img.width, img.height)
    
    width, height = img.size
    font_mono = get_font(20)
    font_small = get_font(16)
    
    # Top right info
    draw.text((width - 250, 60), "4K  |  24 FPS", font=font_mono, fill="#FFFFFF")
    time_str = f"00:{scene_index:02d}:{random.randint(10, 59)}:12"
    draw.text((width - 250, 90), time_str, font=font_mono, fill="#D4AF37")
    
    # Timeline Progress Bar (Bottom)
    progress = scene_index / max(1, total_scenes - 1)
    bar_width = 800
    bar_x = (width - bar_width) // 2
    bar_y = height - 80
    
    # Draw timeline track
    draw.line([(bar_x, bar_y), (bar_x + bar_width, bar_y)], fill="#36454F", width=2)
    # Draw progress
    draw.line([(bar_x, bar_y), (bar_x + int(bar_width * progress), bar_y)], fill="#D4AF37", width=4)
    # Draw current node
    draw.ellipse([(bar_x + int(bar_width * progress) - 5, bar_y - 5), 
                  (bar_x + int(bar_width * progress) + 5, bar_y + 5)], fill="#FFFFFF")
                  
    # Random Investigation Box (Bottom Left)
    draw.rectangle([(60, height - 200), (360, height - 80)], outline="#36454F", width=1)
    draw.text((75, height - 180), "LOCATION DATA", font=font_small, fill="#D4AF37")
    draw.text((75, height - 150), f"COORD: {random.uniform(-90, 90):.4f}° N", font=font_mono, fill="#FFFFFF")
    draw.text((75, height - 120), f"       {random.uniform(-180, 180):.4f}° E", font=font_mono, fill="#FFFFFF")
    
    return np.array(img)

def generate_outro_hud(topic):
    img, draw = create_base_hud()
    
    width, height = img.size
    
    font_title = get_font(70)
    font_sub = get_font(30)
    
    # Center massive cinematic title
    title_text = "THANK YOU FOR WATCHING"
    draw.text((width//2 - len(title_text)*20, height//2 - 150), title_text, font=font_title, fill="#D4AF37")
    
    sub_text = topic.upper()
    draw.text((width//2 - len(sub_text)*8, height//2 - 50), sub_text, font=font_sub, fill="#FFFFFF")
    
    sub_text_2 = "SUBSCRIBE FOR MORE DOCUMENTARIES"
    draw.text((width//2 - len(sub_text_2)*8, height//2 + 50), sub_text_2, font=font_sub, fill="#FFFFFF")
    
    # Draw subscribe box
    box_w = 600
    box_x = (width - box_w) // 2
    box_y = height // 2 + 120
    draw.rectangle([(box_x, box_y), (box_x + box_w, box_y + 60)], outline="#D4AF37", width=2)
    
    return np.array(img)

def generate_focus_hud(topic):
    """A sniper-like focus HUD for zooming in on critical details."""
    img, draw = create_base_hud()
    width, height = img.size
    
    # Draw center crosshairs
    cx, cy = width // 2, height // 2
    draw.line([(cx - 200, cy), (cx - 50, cy)], fill="#FFFFFF", width=2)
    draw.line([(cx + 50, cy), (cx + 200, cy)], fill="#FFFFFF", width=2)
    draw.line([(cx, cy - 200), (cx, cy - 50)], fill="#FFFFFF", width=2)
    draw.line([(cx, cy + 50), (cx, cy + 200)], fill="#FFFFFF", width=2)
    
    # Draw scanning bracket
    draw.rectangle([(cx - 300, cy - 300), (cx + 300, cy + 300)], outline="#D4AF37", width=2)
    
    # Draw blinking text effect
    font_mono = get_font(24)
    draw.text((cx - 150, cy + 320), "ANALYZING EVIDENCE...", font=font_mono, fill="#FF0000")
    
    # Add random data stream on the right
    font_small = get_font(14)
    for i in range(10):
        draw.text((width - 250, 200 + i*20), f"HASH: {random.getrandbits(32):08x}", font=font_small, fill="#36454F")
        
    return np.array(img)

def generate_highlight_hud(topic):
    """A HUD for highlighting a specific artifact or map location."""
    img, draw = create_base_hud()
    width, height = img.size
    
    # Draw a glowing box off-center
    hx, hy = width // 3, height // 2
    draw.rectangle([(hx - 150, hy - 150), (hx + 150, hy + 150)], outline="#FFFFFF", width=3)
    
    # Draw tracking lines to a data panel
    draw.line([(hx + 150, hy), (hx + 300, hy - 100)], fill="#D4AF37", width=2)
    draw.line([(hx + 300, hy - 100), (hx + 500, hy - 100)], fill="#D4AF37", width=2)
    
    # Draw data panel
    draw.rectangle([(hx + 500, hy - 150), (hx + 800, hy - 50)], outline="#36454F", width=2)
    font = get_font(18)
    draw.text((hx + 515, hy - 135), "TARGET IDENTIFIED", font=font, fill="#D4AF37")
    draw.text((hx + 515, hy - 105), f"PROBABILITY: {random.randint(85, 99)}.{random.randint(1,99)}%", font=font, fill="#FFFFFF")
    draw.text((hx + 515, hy - 75), f"MATCH: {topic.upper()}", font=font, fill="#FFFFFF")
    
    return np.array(img)
