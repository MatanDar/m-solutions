#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import random
import requests
import subprocess
import pickle
import re
from datetime import datetime
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from gtts import gTTS
import google.generativeai as genai

# ========================================
# 🔧 הגדרות
# ========================================

# Google Sheets (Service Account)
# קריאת Service Account מקובץ
with open('service-account.json', 'r') as f:
    GOOGLE_SHEETS_CREDENTIALS = f.read()
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')

# Google Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')  # צריך להוסיף!

# YouTube OAuth
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.pickle'

# נתיבים
TEMP_DIR = '/tmp/youtube_videos'
LOGO_PATH = 'logo.png'
MUSIC_PATH = 'background_music.mp3'

# ========================================
# 🤖 יצירת תסריט שיווקי עם Gemini
# ========================================

def generate_marketing_script(product):
    """יוצר תסריט שיווקי בן 30-40 seconds עם Gemini AI"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = f"""
אתה כותב תסריטים למודעות שיווק קצרות ומושכות ביוטיוב.

צור תסריט קצר (30-40 seconds) למוצר הבא:
שם המוצר: {product['title']}
תיאור: {product['description']}
דירוג: {product['rating']}

דרישות:
1. התסריט חייב להיות בעברית בלבד
2. אורך: 60-80 words (כ-30-40 seconds)
3. סגנון: נלהב, אנרגטי, משכנע
4. מבנה:
   - פותח חזק שמושך תשומת לב
   - 2-3 יתרונות מרכזיים של המוצר
   - קריאה לפעולה בסוף
5. השתמש באימוג'ים רלוונטיים
6. אל תכלול כותרות או מספרים - רק טקסט רציף

החזר רק את התסריט, ללא כותרת או הסבר נוסף.
"""
        
        response = model.generate_content(prompt)
        script = response.text.strip()
        
        print(f"✅ Script created ({len(script.split())} words)")
        print(f"📝 Script: {script[:100]}...")
        
        return script
        
    except Exception as e:
        print(f"⚠️ Error creating script: {str(e)}")
        # תסריט ברירת מחדל
        return f"""
היי! רוצים לדעת על המוצר המדהים הזה? 
{product['title']} - המוצר שכולם מדברים עליו!
עם דירוג של {product['rating']} כוכבים, זה חייב להיות טוב!
המחיר? פשוט מטורף! 
אל תפספסו את ההזדמנות הזאת.
לחצו על הלינק בתיאור ותזמינו עכשיו!
"""

# ========================================
# 🎙️ המרת טקסט לדיבור
# ========================================

def text_to_speech(text, output_path):
    """ממיר טקסט לקובץ אודיו בעברית"""
    try:
        # ניקוי אימוג'ים מהטקסט
        text_clean = re.sub(r'[^\w\s\u0590-\u05FF,.!?-]', '', text)
        
        tts = gTTS(text=text_clean, lang='he', slow=False)
        tts.save(output_path)
        
        # בדיקת משך האודיו
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration', '-of',
            'default=noprint_wrappers=1:nokey=1', output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        print(f"✅ Audio created: {duration:.1f} seconds")
        return duration
        
    except Exception as e:
        print(f"❌ Error creating audio: {str(e)}")
        return None

# ========================================
# 📝 יצירת כתוביות SRT
# ========================================

def create_subtitles(script, duration, output_path):
    """יוצר קובץ כתוביות SRT"""
    try:
        words = script.split()
        words_per_second = len(words) / duration
        
        srt_content = []
        subtitle_index = 1
        
        # חלוקה לsentences
        sentences = re.split(r'[.!?]\s+', script)
        current_time = 0
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            sentence_words = sentence.split()
            sentence_duration = len(sentence_words) / words_per_second
            
            start_time = current_time
            end_time = current_time + sentence_duration
            
            # פורמט SRT
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
            srt_content.append(sentence.strip())
            srt_content.append("")
            
            subtitle_index += 1
            current_time = end_time
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_content))
        
        print(f"✅ Subtitles created: {subtitle_index - 1} sentences")
        return True
        
    except Exception as e:
        print(f"❌ Error creating subtitles: {str(e)}")
        return False

def format_srt_time(seconds):
    """ממיר seconds לפורמט SRT (00:00:00,000)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

# ========================================
# 🔊 הורדת מוזיקת רקע
# ========================================

def download_background_music():
    """הורדת מוזיקת רקע חינמית"""
    if os.path.exists(MUSIC_PATH):
        print(f"✅ Music already exists: {MUSIC_PATH}")
        return True
    
    # מוזיקה חינמית מ-Bensound (רישיון Creative Commons)
    music_urls = [
        "https://www.bensound.com/bensound-music/bensound-energy.mp3",
        "https://www.bensound.com/bensound-music/bensound-betterdays.mp3",
        "https://www.bensound.com/bensound-music/bensound-happyrock.mp3"
    ]
    
    for music_url in music_urls:
        try:
            print(f"📥 Trying to download: {music_url}")
            response = requests.get(music_url, timeout=30)
            response.raise_for_status()
            
            with open(MUSIC_PATH, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Music downloaded: {MUSIC_PATH}")
            return True
            
        except Exception as e:
            print(f"⚠️ Failed: {str(e)}")
            continue
    
    # יצירת שקט במקום מוזיקה
    print("⚠️ Creating silent audio instead of music...")
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-t', '60', MUSIC_PATH
    ], capture_output=True)
    return True

# ========================================
# 🔍 פונקציות עזר קיימות
# ========================================

def get_youtube_service():
    """מתחבר ל-YouTube עם OAuth"""
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        print("📂 Loading existing token...")
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing token...")
            creds.refresh(Request())
        else:
            print("🔐 Initial authentication required...")
            print("👉 Browser will open - approve the permissions!")
            
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"❌ Missing file: {CLIENT_SECRET_FILE}")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)
        
        print("💾 Saving token...")
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        print("✅ Token saved!")
    
    return build('youtube', 'v3', credentials=creds)

def get_random_product():
    """בחירת מוצר אקראי מהטבלה"""
    try:
        credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range='Affiliate Table!A2:F'
        ).execute()
        
        products = result.get('values', [])
        
        if not products:
            print("❌ No products in table!")
            return None
        
        product = random.choice(products)
        
        product_data = {
            'url': product[0] if len(product) > 0 else '',
            'title': product[1] if len(product) > 1 else 'מוצר מדהים',
            'description': product[2] if len(product) > 2 else '',
            'image_url': product[3] if len(product) > 3 else '',
            'affiliate_link': product[4] if len(product) > 4 else '',
            'rating': product[5] if len(product) > 5 else 'N/A'
        }
        
        print(f"✅ Selected product: {product_data['title'][:50]}...")
        return product_data
        
    except Exception as e:
        print(f"❌ Error reading product: {str(e)}")
        return None

def download_image(image_url, output_path):
    """הורדת תמונת המוצר"""
    try:
        if 'weserv.nl' in image_url:
            original_url = image_url.split('url=')[1].split('&')[0]
            image_url = f"https://{original_url}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.aliexpress.com/'
        }
        
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Image downloaded: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading image: {str(e)}")
        return False

# ========================================
# 🎬 יצירת סרטון משופר עם קריינות וכתוביות
# ========================================

def create_video_with_voiceover(product, image_path, audio_path, subtitle_path, duration, output_path):
    """יוצר סרטון עם תמונה, קול, כתוביות ומוזיקת רקע"""
    
    try:
        # חישוב משך הסרטון (אודיו + 2 seconds)
        video_duration = duration + 2
        
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            # תמונת המוצר
            '-loop', '1', '-t', str(video_duration), '-i', image_path,
            # לוגו (אופציונלי)
            '-loop', '1', '-t', str(video_duration), '-i', LOGO_PATH,
            # קריינות
            '-i', audio_path,
            # מוזיקת רקע
            '-stream_loop', '-1', '-i', MUSIC_PATH,
            '-filter_complex',
            f"""
            [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,
            pad=1920:1080:(ow-iw)/2:(oh-ih)/2,
            zoompan=z='min(zoom+0.002,1.3)':d={int(video_duration * 25)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080[bg];
            
            [1:v]scale=120:-1[logo];
            
            [bg][logo]overlay=W-w-30:30[vid];
            
            [vid]subtitles={subtitle_path}:force_style='FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=20,Alignment=2'[vout];
            
            [2:a]volume=1.0[voice];
            [3:a]volume=0.15[music];
            [voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]
            """,
            '-map', '[vout]',
            '-map', '[aout]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-t', str(video_duration),
            output_path
        ]
        
        print("🎬 Creating video...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Video created: {output_path}")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

# ========================================
# 📺 העלאה ליוטיוב
# ========================================

def upload_to_youtube(youtube, video_path, product, script):
    """העלאת הסרטון ליוטיוב"""
    try:
        # כותרת קצרה יותר
        title = f"{product['title'][:70]} | מבצע מיוחד!"
        
        description = f"""{script[:200]}...

📦 על המוצר:
{product['description'][:300]}

⭐ דירוג: {product['rating']}

🔥 👇 לחצו כאן לקנייה במחיר מיוחד! 👇 🔥
{product['affiliate_link']}

✅ משלוח מהיר
✅ החזרה קלה
✅ מחירים הכי טובים!

#aliexpress #שופינג #מבצעים #קניות #AliExpressFinds #OnlineShopping #Deals
"""
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['aliexpress', 'shopping', 'deals', 'מוצרים', 'קניות', 'מבצעים'],
                'categoryId': '22'  # People & Blogs
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        print("📤 Uploading to YouTube...")
        response = request.execute()
        
        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        print(f"✅ Video uploaded!")
        print(f"🔗 {video_url}")
        return video_url
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return None

# ========================================
# 🚀 Main
# ========================================

def main():
    print("=" * 60)
    print("🎬 Creating and uploading AI-Powered marketing video to YouTube!")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # בדיקת API Key
    if not GEMINI_API_KEY:
        print("⚠️ Missing GEMINI_API_KEY! Add the variable:")
        print("export GEMINI_API_KEY='your-api-key'")
        return
    
    # יצירת תיקייה זמנית
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # הורדת מוזיקה
    print("\n🎵 Downloading background music...")
    download_background_music()
    
    # חיבור ליוטיוב
    print("\n🔐 Connecting to YouTube...")
    youtube = get_youtube_service()
    if not youtube:
        print("❌ Failed to connect to YouTube")
        return
    print("✅ Connected to YouTube!")
    
    # בחירת מוצר
    print("\n📦 Selecting random product...")
    product = get_random_product()
    if not product:
        print("❌ Product not found")
        return
    
    # יצירת תסריט AI
    print("\n🤖 Creating marketing script with Gemini AI...")
    script = generate_marketing_script(product)
    
    # המרה לאודיו
    print("\n🎙️ Converting to voiceover...")
    audio_path = os.path.join(TEMP_DIR, 'voiceover.mp3')
    duration = text_to_speech(script, audio_path)
    if not duration:
        print("❌ Failed to create audio")
        return
    
    # יצירת כתוביות
    print("\n📝 Creating subtitles...")
    subtitle_path = os.path.join(TEMP_DIR, 'subtitles.srt')
    create_subtitles(script, duration, subtitle_path)
    
    # הורדת תמונה
    print("\n🖼️ Downloading product image...")
    image_path = os.path.join(TEMP_DIR, 'product_image.jpg')
    if not download_image(product['image_url'], image_path):
        print("❌ כישלון בהורדת תמונה")
        return
    
    # יצירת סרטון
    print("\n🎬 Creating video...")
    video_path = os.path.join(TEMP_DIR, 'final_video.mp4')
    if not create_video_with_voiceover(product, image_path, audio_path, subtitle_path, duration, video_path):
        print("❌ Failed to create video")
        return
    
    # העלאה ליוטיוב
    print("\n📺 Uploading to YouTube...")
    video_url = upload_to_youtube(youtube, video_path, product, script)
    
    if video_url:
        print("\n🎉 Everything completed successfully!")
        print(f"🔗 Link: {video_url}")
    
    # ניקוי
    print("\n🧹 Cleaning temporary files...")
    for file in [image_path, audio_path, subtitle_path, video_path]:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n✅ Done!")

if __name__ == "__main__":
    main()