#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import random
import requests
import subprocess
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========================================
# 🔧 הגדרות
# ========================================

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')

# YouTube
YOUTUBE_CREDENTIALS = os.environ.get('YOUTUBE_CREDENTIALS')

# נתיבים
TEMP_DIR = '/tmp/youtube_videos'
LOGO_PATH = 'logo.png'
MUSIC_PATH = 'background_music.mp3'

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
        
        # קריאת כל המוצרים
        result = sheet.values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range='Affiliate Table!A2:F'  # מדלג על Header
        ).execute()
        
        products = result.get('values', [])
        
        if not products:
            print("❌ אין מוצרים בטבלה!")
            return None
        
        # בחירה אקראית
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
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ תמונה הורדה: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בהורדת תמונה: {str(e)}")
        return False

# ========================================
# 🎬 יצירת סרטון עם FFmpeg
# ========================================

def create_video(product, image_path, output_path):
    """יצירת סרטון 15 שניות עם אנימציות וטקסט"""
    
    title = product['title'][:80]
    rating = product['rating']
    
    # הכנת הטקסטים
    text1 = f"😍 {title}"
    text2 = f"⭐ דירוג: {rating}"
    text3 = "🔥 מוצר חם!"
    text4 = "👇 לחצו על הלינק!"
    
    # פקודת FFmpeg
    # זה יוצר סרטון 15 שניות עם:
    # - Zoom In/Out על התמונה
    # - 4 טקסטים שמופיעים בזמנים שונים
    # - הלוגו בפינה
    # - מוזיקת רקע
    
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', image_path,  # תמונת המוצר
        '-i', LOGO_PATH,  # הלוגו
        '-i', MUSIC_PATH,  # מוזיקה
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
        '-map', '2:a',  # אודיו מהמוזיקה
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        '-t', '15',  # 15 שניות
        output_path
    ]
    
    try:
        print("🎬 יוצר סרטון...")
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ סרטון נוצר: {output_path}")
            return True
        else:
            print(f"❌ שגיאה ביצירת סרטון: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה: {str(e)}")
        return False

# ========================================
# 📺 העלאה ליוטיוב
# ========================================

def upload_to_youtube(video_path, product):
    """העלאת הסרטון ליוטיוב"""
    try:
        credentials_dict = json.loads(YOUTUBE_CREDENTIALS)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/youtube.upload']
        )
        
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # כותרת הסרטון
        title = f"💥 המוצר שכולם מחפשים! {product['title'][:50]}"
        
        # תיאור הסרטון
        description = f"""🔥 {product['description']}
⭐ דירוג: {product['rating']}

🛒 קנו עכשיו:
{product['affiliate_link']}

#aliexpress #מוצרים #קניות #deals #shopping
"""
        
        # העלאה
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': ['aliexpress', 'shopping', 'deals', 'מוצרים', 'קניות'],
                'categoryId': '22'  # People & Blogs
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
        
        response = request.execute()
        
        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        print(f"✅ סרטון הועלה ליוטיוב: {video_url}")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בהעלאה ליוטיוב: {str(e)}")
        return False

# ========================================
# 🎵 הורדת מוזיקת רקע חינמית
# ========================================

def download_background_music():
    """הורדת מוזיקת רקע חינמית"""
    # מוזיקה חינמית מ-YouTube Audio Library
    # זו מוזיקה אנרגטית קצרה ללא זכויות יוצרים
    music_url = "https://www.bensound.com/bensound-music/bensound-energy.mp3"
    
    try:
        response = requests.get(music_url, timeout=30)
        response.raise_for_status()
        
        with open(MUSIC_PATH, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ מוזיקה הורדה: {MUSIC_PATH}")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בהורדת מוזיקה: {str(e)}")
        # אם לא מצליח להוריד, ניצור שקט
        subprocess.run([
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
            '-t', '15', MUSIC_PATH
        ])
        return True

# ========================================
# 🚀 Main
# ========================================

def main():
    print("=" * 50)
    print("🎬 יוצר סרטון ליוטיוב!")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # יצירת תיקייה זמנית
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # הורדת מוזיקת רקע (פעם אחת)
    if not os.path.exists(MUSIC_PATH):
        download_background_music()
    
    # 1. בחירת מוצר אקראי
    product = get_random_product()
    if not product:
        return
    
    # 2. הורדת תמונה
    image_path = os.path.join(TEMP_DIR, 'product_image.jpg')
    if not download_image(product['image_url'], image_path):
        return
    
    # 3. יצירת סרטון
    video_path = os.path.join(TEMP_DIR, 'output_video.mp4')
    if not create_video(product, image_path, video_path):
        return
    
    # 4. העלאה ליוטיוב
    if upload_to_youtube(video_path, product):
        print("🎉 הכל הושלם בהצלחה!")
    
    # ניקוי
    print("🧹 מנקה קבצים זמניים...")
    if os.path.exists(image_path):
        os.remove(image_path)
    if os.path.exists(video_path):
        os.remove(video_path)

if __name__ == "__main__":
    main()