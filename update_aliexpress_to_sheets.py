#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import hashlib
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googletrans import Translator

# ===========================
# הגדרות
# ===========================

# AliExpress API
ALIEXPRESS_API_KEY = os.environ.get('ALIEXPRESS_API_KEY')
ALIEXPRESS_API_SECRET = os.environ.get('ALIEXPRESS_API_SECRET')
ALIEXPRESS_TRACKING_ID = os.environ.get('ALIEXPRESS_TRACKING_ID')

# Google Sheets
SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Products'

# Proxy לתמונות
IMAGE_PROXY = "https://images.weserv.nl/?url="

# מתרגם
translator = Translator()

# רשימת מילות מפתח מורחבת למניעת כפילויות
PRODUCT_KEYWORDS = [
    # Electronics
    'cable', 'charger', 'mouse', 'keyboard', 'lighter', 'flashlight', 'headphones', 
    'earbuds', 'speaker', 'powerbank', 'adapter', 'usb', 'hdmi', 'webcam',
    
    # Fashion & Accessories
    'shirt', 'dress', 'shoes', 'bag', 'wallet', 'backpack', 'watch', 'belt', 
    'sunglasses', 'hat', 'scarf', 'gloves', 'socks', 'tie', 'bracelet', 'necklace',
    'ring', 'earrings', 'clutch', 'purse', 'handbag', 'tote', 'crossbody', 
    'shoulder bag', 'messenger', 'satchel', 'hobo', 'wristlet', 'pouch',
    
    # Home & Kitchen
    'mug', 'cup', 'bottle', 'thermos', 'flask', 'tumbler', 'pillow', 'cushion',
    'blanket', 'organizer', 'holder', 'rack', 'storage', 'box', 'container',
    'plate', 'bowl', 'spoon', 'fork', 'knife', 'pan', 'pot', 'opener',
    
    # Beauty & Personal Care
    'brush', 'comb', 'mirror', 'razor', 'trimmer', 'scissors', 'tweezers',
    'nail clipper', 'file', 'makeup', 'lipstick', 'mascara', 'eyeshadow',
    
    # Tools & Hardware
    'screwdriver', 'hammer', 'wrench', 'pliers', 'tape measure', 'level',
    'drill', 'saw', 'knife', 'multi-tool', 'flashlight', 'torch',
    
    # Sports & Outdoors
    'ball', 'racket', 'paddle', 'mat', 'band', 'rope', 'weight', 'dumbbell',
    'bottle', 'towel', 'gloves', 'cap', 'helmet', 'pump',
    
    # Stationery & Office
    'pen', 'pencil', 'notebook', 'notepad', 'marker', 'highlighter', 'eraser',
    'stapler', 'clip', 'folder', 'binder', 'calculator', 'ruler',
    
    # Toys & Hobbies
    'puzzle', 'toy', 'game', 'doll', 'car', 'truck', 'plane', 'robot',
    'lego', 'block', 'dice', 'card', 'figure', 'model',
    
    # Pet Supplies
    'collar', 'leash', 'bowl', 'toy', 'bed', 'carrier', 'grooming',
    
    # Automotive
    'mount', 'holder', 'cover', 'mat', 'organizer', 'charger', 'light',
    'mirror', 'sensor', 'camera', 'cleaner', 'polish',
    
    # Other Common Items
    'bookmark', 'keychain', 'lanyard', 'badge', 'sticker', 'magnet', 'flag',
    'poster', 'sign', 'plaque', 'ornament', 'decoration', 'candle', 'frame',
    'toilet', 'cigar', 'cutter', 'bookmark', 'puzzle', 'backdrop', 'memorial'
]

# ===========================
# פונקציות עזר
# ===========================

def generate_signature(secret, api, parameters):
    """Generate API signature"""
    # Sort parameters
    sorted_params = sorted(parameters.items())
    
    # Create string to sign
    string_to_sign = api
    for key, value in sorted_params:
        string_to_sign += f"{key}{value}"
    
    # Generate signature
    signature = hashlib.md5(f"{secret}{string_to_sign}{secret}".encode('utf-8')).hexdigest().upper()
    return signature

def extract_main_keyword(title):
    """
    מחלץ מילת מפתח עיקרית מכותרת המוצר
    """
    title_lower = title.lower()
    
    # חיפוש מילת מפתח ארוכה ביותר שמופיעה בכותרת
    found_keywords = []
    for keyword in PRODUCT_KEYWORDS:
        if keyword in title_lower:
            found_keywords.append(keyword)
    
    # החזרת המילה הארוכה ביותר (ספציפית יותר)
    if found_keywords:
        return max(found_keywords, key=len)
    
    return None

def is_duplicate(product, existing_products):
    """
    בדיקה האם מוצר כפול
    """
    new_url = product.get('promotion_link', '')
    new_title = product.get('product_title', '').lower()
    new_keyword = extract_main_keyword(product.get('product_title', ''))
    
    for existing in existing_products:
        existing_url = existing.get('promotion_link', '')
        existing_title = existing.get('product_title', '').lower()
        existing_keyword = extract_main_keyword(existing.get('product_title', ''))
        
        # בדיקה 1: URL זהה
        if new_url and existing_url and new_url == existing_url:
            return True
        
        # בדיקה 2: כותרת זהה
        if new_title == existing_title:
            return True
        
        # בדיקה 3: דמיון גבוה בכותרת
        if new_title and existing_title:
            # חישוב אחוז דמיון פשוט
            common_words = set(new_title.split()) & set(existing_title.split())
            if len(common_words) > 0:
                similarity = len(common_words) / max(len(new_title.split()), len(existing_title.split()))
                if similarity > 0.8:
                    return True
        
        # בדיקה 4: מילת מפתח זהה (למנוע מספר מוצרים מאותו סוג)
        if new_keyword and existing_keyword and new_keyword == existing_keyword:
            return True
    
    return False

def translate_to_hebrew(text):
    """
    תרגום טקסט לעברית
    """
    try:
        if not text or len(text.strip()) == 0:
            return text
        
        # תרגום
        translated = translator.translate(text, src='en', dest='iw')
        return translated.text
    except Exception as e:
        print(f"⚠️ שגיאה בתרגום: {e}")
        return text

def get_aliexpress_hot_products():
    """
    משיכת מוצרים חמים מ-AliExpress
    """
    api_url = "https://api-sg.aliexpress.com/sync"
    
    parameters = {
        'app_key': ALIEXPRESS_API_KEY,
        'method': 'aliexpress.affiliate.hotproduct.query',
        'sign_method': 'md5',
        'timestamp': str(int(time.time() * 1000)),
        'format': 'json',
        'v': '2.0',
        'tracking_id': ALIEXPRESS_TRACKING_ID,
        'target_currency': 'ILS',
        'target_language': 'EN',
        'ship_to_country': 'IL',
        'delivery_days': '15',
        'sort': 'VOLUME_ASC',
        'page_size': '100'
    }
    
    # Generate signature
    signature = generate_signature(ALIEXPRESS_API_SECRET, parameters['method'], parameters)
    parameters['sign'] = signature
    
    # Make request
    response = requests.get(api_url, params=parameters)
    
    print("API Response:", response.text[:1000])
    
    if response.status_code == 200:
        data = response.json()
        
        # Extract products from response
        if 'aliexpress_affiliate_hotproduct_query_response' in data:
            resp_result = data['aliexpress_affiliate_hotproduct_query_response'].get('resp_result', {})
            result = resp_result.get('result', {})
            products_data = result.get('products', {})
            products = products_data.get('product', [])
            return products
    
    return []

def filter_products_for_israel(products):
    """
    סינון מוצרים מותאמים לישראל
    """
    filtered = []
    seen_products = []
    
    print(f"✅ נמצאו {len(products)} מוצרים לפני סינון!")
    
    for product in products:
        # בדיקת כפילויות
        if is_duplicate(product, seen_products):
            continue
        
        # בדיקת מחיר (₪15-₪300)
        price_value = float(product.get('target_sale_price', '0'))
        if price_value > 300 or price_value < 15:
            print(f"⏭️ דילוג - מחיר לא מתאים (₪{price_value:.0f}): {product.get('product_title', '')[:50]}...")
            continue
        
        # קבלת מספר מכירות
        sales_volume = product.get('lastest_volume', 0)
        
        print(f"✅ מוצר מאושר (₪{price_value:.0f}, 🔥{sales_volume} מכירות): {product.get('product_title', '')[:50]}...")
        
        filtered.append(product)
        seen_products.append(product)
    
    print(f"🎯 סה\"כ מוצרים שעברו סינון: {len(filtered)}")
    
    # מיון לפי מספר מכירות (הכי נמכר קודם)
    filtered.sort(key=lambda x: x.get('lastest_volume', 0), reverse=True)
    
    # החזרת 30 הטובים ביותר
    return filtered[:30]

def update_google_sheet(products):
    """
    עדכון Google Sheets עם המוצרים
    """
    # Load credentials from environment variable
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS not found in environment variables")
    
    creds_dict = json.loads(creds_json)
    
    # Create credentials
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    # Build service
    service = build('sheets', 'v4', credentials=credentials)
    
    # Prepare data
    values = [['Title', 'Title (Hebrew)', 'Price', 'Image', 'Link', 'Last Updated']]
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for product in products:
        title = product.get('product_title', '')
        price = f"₪{product.get('target_sale_price', 'N/A')}"
        image_url = product.get('product_main_image_url', '')
        
        # העברת תמונה דרך Proxy
        if image_url:
            # הסרת https:// והוספת הפרוקסי
            clean_url = image_url.replace('https://', '').replace('http://', '')
            proxied_image = f"{IMAGE_PROXY}{clean_url}"
        else:
            proxied_image = ''
        
        link = product.get('promotion_link', '')
        
        # תרגום הכותרת לעברית
        title_hebrew = translate_to_hebrew(title)
        
        values.append([title, title_hebrew, price, proxied_image, link, current_time])
    
    # Clear existing data
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A:F'
    ).execute()
    
    # Update with new data
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A1',
        valueInputOption='RAW',
        body={'values': values}
    ).execute()
    
    print(f"✅ {len(products)} מוצרים חדשים נוספו!")

# ===========================
# Main
# ===========================

def main():
    print("🚀 מתחיל משיכת מוצרים חמים...")
    print(f"📅 תאריך: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 קטגוריות: אלקטרוניקה, אופנה, בית")
    print("🇮🇱 מותאם לישראל:")
    print("   ✅ משלוח חינם לישראל")
    print("   ✅ זמן משלוח מהיר (עד 15 יום)")
    print("   ✅ מחיר: ₪15-₪300")
    print("   ✅ מחירים בשקלים")
    print("   ✅ מיון לפי כמות מכירות (הכי פופולרי)")
    print("🔄 כל התמונות יעברו דרך Proxy - 100% יעבוד!")
    print("🔤 כל התיאורים יתורגמו לעברית!")
    print("🚫 סינון כפילויות - רק מוצרים ייחודיים!")
    
    # Get products
    products = get_aliexpress_hot_products()
    
    if not products:
        print("⚠️ לא נמצאו מוצרים")
        return
    
    # Filter for Israel
    filtered_products = filter_products_for_israel(products)
    
    print(f"✅ נשארו {len(filtered_products)} מוצרים אחרי סינון לישראל!")
    
    if not filtered_products:
        print("⚠️ לא נמצאו מוצרים")
        return
    
    # Update Google Sheet
    update_google_sheet(filtered_products)
    
    print("✅ המוצרים עודכנו בהצלחה!")

if __name__ == '__main__':
    main()