# 🎥 Fully Automated YouTube & Facebook Documentary Engine

A completely autonomous, server-side Python automation engine that generates, edits, and publishes high-quality cinematic documentaries to YouTube and Facebook every single day without human intervention.

## 🚀 Features

*   **📈 Trending Topic Discovery:** Automatically scrapes the most trending global topics daily using the Wikipedia API to ensure high audience retention and search volume.
*   **🧠 AI Script Generation:** Hooks into NVIDIA's blazing fast LLM infrastructure (NVIDIA NIM) to generate detailed, suspenseful documentary scripts with precise search queries for stock footage.
*   **🎬 Cinematic Video Editing:** Uses `MoviePy` to resize, crop (1080p widescreen), and color-grade (contrast and luminance tweaks) raw footage from Pexels to create a premium Netflix/NatGeo aesthetic.
*   **🎙️ AI Voiceovers:** Utilizes `edge-tts` to generate deep, realistic documentary-style narration with built-in voice fallbacks to prevent crashes.
*   **📊 Procedural HUD Overlays:** Dynamically draws transparent investigation UI elements (Focus panels, Title cards, Location data, Audio meters) frame-by-frame using `PIL` to keep visual engagement high.
*   **☁️ Cloud Auto-Publishing:** Integrates with the YouTube Data API v3 and the Facebook Graph Video API (utilizing the Resumable Upload Chunking Protocol) to bypass size limits and upload directly from the server.
*   **🧹 Self-Cleaning:** Deep-cleans its own working directories after successful uploads to prevent cloud storage bloat.

## ⚙️ Architecture & Deployment

This project is built to run 100% headless via **GitHub Actions**.

The repository utilizes an `ubuntu-latest` runner equipped with `ffmpeg` and `ImageMagick`. To bypass bot-detection algorithms, the rendering workflow is triggered every day at 09:30 UTC, with natural rendering time-variances creating organic, unpredictable upload times.

### 🔐 Security Notice
This repository handles highly sensitive OAuth tokens and API keys. To deploy this yourself, you must never hardcode your keys. The script is configured to pull the following variables directly from GitHub Secrets:

*   `YOUTUBE_CLIENT_SECRETS`
*   `YOUTUBE_CREDENTIALS`
*   `FACEBOOK_PAGE_ID`
*   `FACEBOOK_ACCESS_TOKEN`
*   `NVIDIA_NIM_API_KEY`
*   `PEXELS_API_KEY`

## 🛠️ Built With
*   **Python 3.10**
*   **MoviePy** (Video Compositing)
*   **Pillow** (Procedural Graphics)
*   **Requests** (REST API integrations)
*   **Google OAuth & API Client** (YouTube Uploads)

---
*Built for absolute automation.*
