#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import random
import requests
import subprocess
import pickle
from datetime import datetime
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========================================
# 🔧 הגדרות
# ========================================

# Google Sheets (Service Account - נשאר כמו שהיה!)
GOOGLE_SHEETS_CREDENTIALS = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')

# YouTube OAuth (חדש!)
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.pickle'

# נתיבים
TEMP_DIR = '/tmp/youtube_videos'
LOGO_PATH = 'logo.png'
MUSIC_PATH = 'background_music.mp3'

# ========================================
# 🔐 אימות YouTube עם OAuth
# ========================================

def get_youtube_service():
    """מתחבר ל-YouTube עם OAuth"""
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    
    creds = None
    
    # בדיקה אם יש token שמור
    if os.path.exists(TOKEN_FILE):
        print("📂 טוען token קיים...")
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # אם אין token או שהוא לא תקף
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 מרענן token...")
            creds.refresh(Request())
        else:
            print("🔐 נדרש אימות ראשוני...")
            print("👉 דפדפן ייפתח - אשר את ההרשאות!")
            
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"❌ חסר קובץ: {CLIENT_SECRET_FILE}")
                print("👉 הורד את client_secret.json מ-Google Cloud!")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)
        
        # שמירת token
        print("💾 שומר token...")
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        print("✅ Token נשמר!")
    
    return build('youtube', 'v3', credentials=creds)

# ========================================
# 📊 קריאת מוצר אקראי מ-Google Sheets
# ========================================

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
            print("❌ אין מוצרים בטבלה!")
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
        
        print(f"✅ נבחר מוצר: {product_data['title'][:50]}...")
        return product_data
        
    except Exception as e:
        print(f"❌ שגיאה בקריאת מוצר: {str(e)}")
        return None

# ========================================
# 🖼️ הורדת תמונת המוצר
# ========================================

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
        
        print(f"✅ תמונה הורדה: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בהורדת תמונה: {str(e)}")
        return False

# ========================================
# 🎵 הורדת מוזיקת רקע
# ========================================

def download_background_music():
    """הורדת מוזיקת רקע חינמית"""
    if os.path.exists(MUSIC_PATH):
        print(f"✅ מוזיקה כבר קיימת: {MUSIC_PATH}")
        return True
    
    music_url = "https://www.bensound.com/bensound-music/bensound-energy.mp3"
    
    try:
        response = requests.get(music_url, timeout=30)
        response.raise_for_status()
        
        with open(MUSIC_PATH, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ מוזיקה הורדה: {MUSIC_PATH}")
        return True
        
    except Exception as e:
        print(f"⚠️ שקט במקום מוזיקה...")
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-t', '15', MUSIC_PATH
        ], capture_output=True)
        return True

# ========================================
# 🎬 יצירת סרטון עם FFmpeg
# ========================================

def create_video(product, image_path, output_path):
    """יצירת סרטון 15 שניות"""
    
    title = product['title'][:80]
    rating = product['rating']
    
    text1 = f"😍 {title}"
    text2 = f"⭐ דירוג: {rating}"
    text3 = "🔥 מוצר חם!"
    text4 = "👇 לחצו על הלינק!"
    
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', image_path,
        '-i', LOGO_PATH,
        '-i', MUSIC_PATH,
        '-filter_complex',
        f"""
        [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,
        pad=1920:1080:(ow-iw)/2:(oh-ih)/2,
        zoompan=z='min(zoom+0.0015,1.5)':d=375:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080[bg];
        
        [1:v]scale=150:-1[logo];
        
        [bg][logo]overlay=W-w-20:20[v1];
        
        [v1]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:
        text='{text1}':fontsize=60:fontcolor=white:
        box=1:boxcolor=black@0.7:boxborderw=10:
        x=(w-text_w)/2:y=200:
        enable='between(t,3,6)'[v2];
        
        [v2]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:
        text='{text2}':fontsize=50:fontcolor=yellow:
        box=1:boxcolor=black@0.7:boxborderw=10:
        x=(w-text_w)/2:y=300:
        enable='between(t,6,9)'[v3];
        
        [v3]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:
        text='{text3}':fontsize=55:fontcolor=orange:
        box=1:boxcolor=black@0.7:boxborderw=10:
        x=(w-text_w)/2:y=400:
        enable='between(t,9,12)'[v4];
        
        [v4]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:
        text='{text4}':fontsize=50:fontcolor=lime:
        box=1:boxcolor=black@0.7:boxborderw=10:
        x=(w-text_w)/2:y=500:
        enable='between(t,12,15)'[vout]
        """,
        '-map', '[vout]',
        '-map', '2:a',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        '-t', '15',
        output_path
    ]
    
    try:
        print("🎬 יוצר סרטון...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ סרטון נוצר: {output_path}")
            return True
        else:
            print(f"❌ שגיאה: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה: {str(e)}")
        return False

# ========================================
# 📺 העלאה ליוטיוב
# ========================================

def upload_to_youtube(youtube, video_path, product):
    """העלאת הסרטון ליוטיוב"""
    try:
        title = f"💥 המוצר שכולם מחפשים! {product['title'][:50]}"
        
        description = f"""🔥 {product['description']}
⭐ דירוג: {product['rating']}

🛒 קנו עכשיו:
{product['affiliate_link']}

#aliexpress #מוצרים #קניות #deals #shopping
"""
        
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['aliexpress', 'shopping', 'deals', 'מוצרים', 'קניות'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public'
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        print("📤 מעלה ליוטיוב...")
        response = request.execute()
        
        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        print(f"✅ סרטון הועלה!")
        print(f"🔗 {video_url}")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בהעלאה: {str(e)}")
        return False

# ========================================
# 🚀 Main
# ========================================

def main():
    print("=" * 60)
    print("🎬 יוצר ומעלה סרטון ליוטיוב!")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # יצירת תיקייה זמנית
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # הורדת מוזיקה
    if not os.path.exists(MUSIC_PATH):
        download_background_music()
    
    # חיבור ליוטיוב
    print("\n🔐 מתחבר ליוטיוב...")
    youtube = get_youtube_service()
    if not youtube:
        return
    print("✅ מחובר ליוטיוב!")
    
    # בחירת מוצר
    print("\n📦 בוחר מוצר...")
    product = get_random_product()
    if not product:
        return
    
    # הורדת תמונה
    print("\n🖼️ מוריד תמונה...")
    image_path = os.path.join(TEMP_DIR, 'product_image.jpg')
    if not download_image(product['image_url'], image_path):
        return
    
    # יצירת סרטון
    print("\n🎬 יוצר סרטון...")
    video_path = os.path.join(TEMP_DIR, 'output_video.mp4')
    if not create_video(product, image_path, video_path):
        return
    
    # העלאה ליוטיוב
    print("\n📺 מעלה ליוטיוב...")
    if upload_to_youtube(youtube, video_path, product):
        print("\n🎉 הכל הושלם בהצלחה!")
    
    # ניקוי
    print("\n🧹 מנקה...")
    if os.path.exists(image_path):
        os.remove(image_path)
    if os.path.exists(video_path):
        os.remove(video_path)
    
    print("\n✅ סיימנו!")

if __name__ == "__main__":
    main()