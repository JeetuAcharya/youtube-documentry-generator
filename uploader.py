import os
import pickle
import google.oauth2.credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
import json

# YouTube API Setup
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secrets.json")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")

# Facebook API Setup (Resolved at runtime)

def get_authenticated_service():
    """Gets the authenticated YouTube service."""
    creds = None
    
    if os.path.exists(CREDENTIALS_FILE):
        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)
        except Exception:
            try:
                with open(CREDENTIALS_FILE, 'rb') as token:
                    creds = pickle.load(token)
            except Exception:
                creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing YouTube credentials...")
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
                
        if not creds:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError(f"[ERROR] client_secrets.json not found at: {CLIENT_SECRETS_FILE}")
            
            print("Launching browser flow for OAuth authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        try:
            with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Warning: Could not save credentials: {e}")

    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(video_path, title, description, tags=None, privacy_status="public"):
    """Uploads a video to YouTube."""
    if not os.path.exists(video_path):
        print(f"File to upload not found: {video_path}")
        return None
        
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"Error authenticating to YouTube: {e}")
        return None

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "24"  # Entertainment category
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }
    
    if tags:
        body["snippet"]["tags"] = tags

    media_body = MediaFileUpload(
        video_path, 
        mimetype="video/mp4", 
        chunksize=1024 * 1024, 
        resumable=True
    )
    
    print(f"Uploading '{title}' to YouTube...")
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_body
    )
    
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"YouTube Uploaded {int(status.progress() * 100)}%...")
        except Exception as e:
            print(f"An error occurred during YouTube upload: {e}")
            return None

    video_id = response.get("id")
    print(f"Successfully uploaded to YouTube! Video ID: {video_id}")
    return video_id

def pin_comment(video_id, text):
    """Posts a top-level comment on the video to kickstart algorithm engagement."""
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"Error authenticating for comment: {e}")
        return False
        
    print(f"Posting top-level comment to video {video_id}...")
    try:
        request = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": text
                        }
                    }
                }
            }
        )
        response = request.execute()
        print("Successfully posted comment!")
        return True
    except Exception as e:
        print(f"Failed to post comment: {e}")
        return False


def upload_to_facebook_video(video_file, title, description):
    """
    Uploads an MP4 file directly to a Facebook Page as a standard Video (not a Reel).
    """
    FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "YOUR_FB_PAGE_ID")
    FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "YOUR_FB_TOKEN")
    
    if not FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ID == "YOUR_FB_PAGE_ID" or not FACEBOOK_ACCESS_TOKEN:
        print("Facebook Page ID or Access Token is missing or not set in environment.")
        return False
        
    print(f"Initializing Facebook Video upload for Page ID: {FACEBOOK_PAGE_ID}")
    
    # Use standard videos endpoint instead of video_reels. Must use graph-video subdomain.
    url = f"https://graph-video.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/videos"
    
    payload = {
        'access_token': FACEBOOK_ACCESS_TOKEN,
        'title': title,
        'description': description
    }
    
    print("Uploading video to Facebook servers (this may take a few minutes for large files)...")
    
    try:
        # Step 1: START PHASE
        file_size = os.path.getsize(video_file)
        start_payload = {
            'access_token': FACEBOOK_ACCESS_TOKEN,
            'upload_phase': 'start',
            'file_size': file_size
        }
        res = requests.post(url, data=start_payload)
        res.raise_for_status()
        session_data = res.json()
        
        upload_session_id = session_data['upload_session_id']
        start_offset = int(session_data['start_offset'])
        end_offset = int(session_data['end_offset'])
        
        # Step 2: TRANSFER PHASE
        with open(video_file, 'rb') as f:
            while start_offset < file_size:
                f.seek(start_offset)
                chunk_length = end_offset - start_offset
                chunk = f.read(chunk_length)
                
                transfer_payload = {
                    'access_token': FACEBOOK_ACCESS_TOKEN,
                    'upload_phase': 'transfer',
                    'upload_session_id': upload_session_id,
                    'start_offset': start_offset
                }
                files = {'video_file_chunk': chunk}
                
                # Retry logic for Facebook's unstable Graph API
                max_retries = 5
                for attempt in range(max_retries):
                    print(f"Uploading chunk... ({start_offset}/{file_size} bytes) [Attempt {attempt+1}]")
                    res = requests.post(url, data=transfer_payload, files=files, timeout=60)
                    
                    if res.status_code == 200:
                        break
                    elif res.status_code >= 500:
                        print(f"Facebook Server Error 500. Retrying in 5 seconds...")
                        import time
                        time.sleep(5)
                        if attempt == max_retries - 1:
                            res.raise_for_status()
                    else:
                        res.raise_for_status()
                
                transfer_data = res.json()
                
                start_offset = int(transfer_data['start_offset'])
                end_offset = int(transfer_data['end_offset'])
                
        # Step 3: FINISH PHASE
        print("Finalizing upload and publishing...")
        finish_payload = {
            'access_token': FACEBOOK_ACCESS_TOKEN,
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'title': title,
            'description': description
        }
        res = requests.post(url, data=finish_payload)
        res.raise_for_status()
        finish_data = res.json()
        
        # Facebook returns 'success': True on finish phase usually
        if finish_data.get("success"):
            print("Facebook Video Upload Complete! Processing on Facebook's end...")
            return True
        else:
            print(f"Facebook API failed during finish phase: {finish_data}")
            return False
            
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err.response.status_code}")
        print(f"Facebook API Response: {err.response.text}")
        return False
    except Exception as e:
        print(f"Failed to upload video to Facebook. Connection/System Error: {str(e)}")
        return False
