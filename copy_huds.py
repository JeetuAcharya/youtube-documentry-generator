import os
import shutil
import glob

brain_dir = r"C:\Users\BrahmaputraGame\.gemini\antigravity\brain\da736e65-b0ff-40ca-ac0b-f21a2115152f"
target_dir = r"C:\Youtube Documentary Automation\Assets\HUDs"
os.makedirs(target_dir, exist_ok=True)

huds = {
    "intro_hud": "intro_hud_*.png",
    "location_hud": "location_hud_*.png",
    "case_file_hud": "case_file_hud_*.png",
    "timeline_hud": "timeline_hud_*.png",
    "evidence_hud": "evidence_hud_*.png",
    "quote_hud": "quote_hud_*.png",
    "map_hud": "map_hud_*.png",
    "outro_hud": "outro_hud_*.png"
}

for name, pattern in huds.items():
    matches = glob.glob(os.path.join(brain_dir, pattern))
    if matches:
        source = matches[-1] # Take the latest match
        dest = os.path.join(target_dir, f"{name}.png")
        shutil.copy2(source, dest)
        print(f"Copied {os.path.basename(source)} to {dest}")
    else:
        print(f"Could not find match for {pattern}")
