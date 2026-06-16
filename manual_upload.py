import uploader
import os

video_path = r"C:\Youtube Documentary Automation\final_documentary.mp4"

# Set a generic catchy title since we don't know the exact topic of the old video
title = "The Terrifying Truth of Unsolved Mysteries 🚨"
description = "What is the real secret behind these mysteries? Watch to find out.\n\n#UnsolvedMysteries #documentary #mystery #history"

if os.path.exists(video_path):
    print("Found an existing video! Starting manual upload phase...")
    
    print("\n--- Uploading to YouTube ---")
    uploader.upload_to_youtube(video_path, title, description, privacy_status="public")
    
    print("\n--- Uploading to Facebook ---")
    uploader.upload_to_facebook_video(video_path, title, description)
    
    print("\nUploads complete! (I will not delete this file so you can keep a copy).")
else:
    print("No 'final_documentary.mp4' found in the directory to upload.")
