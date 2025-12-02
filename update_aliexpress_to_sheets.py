#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googletrans import Translator
import time

# ===========================
# הגדרות
# ===========================

# Google Sheets
SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

# Proxy לתמונות
IMAGE_PROXY = "https://images.weserv.nl/?url="

# מתרגם
translator = Translator()

# User Agent לדפדפן
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

# רשימת מילות מפתח למניעת כפילויות
PRODUCT_KEYWORDS = [
    'cable', 'charger', 'mouse', 'keyboard', 'lighter', 'flashlight', 'headphones', 
    'earbuds', 'speaker', 'powerbank', 'adapter', 'usb', 'hdmi', 'webcam',
    'shirt', 'dress', 'shoes', 'bag', 'wallet', 'backpack', 'watch', 'belt', 
    'sunglasses', 'hat', 'scarf', 'gloves', 'socks', 'tie', 'bracelet', 'necklace',
    'ring', 'earrings', 'clutch', 'purse', 'handbag', 'tote', 'crossbody',
    'mug', 'cup', 'bottle', 'thermos', 'flask', 'tumbler', 'pillow', 'cushion',
    'blanket', 'organizer', 'holder', 'rack', 'storage', 'box', 'container',
    'brush', 'comb', 'mirror', 'razor', 'trimmer', 'scissors', 'tweezers',
    'pen', 'pencil', 'notebook', 'marker', 'toy', 'puzzle', 'game'
]

# ===========================
# פונקציות עזר
# ===========================

def extract_main_keyword(title):
    """מחלץ מילת מפתח עיקרית מכותרת"""
    title_lower = title.lower()
    found_keywords = []
    for keyword in PRODUCT_KEYWORDS:
        if keyword in title_lower:
            found_keywords.append(keyword)
    if found_keywords:
        return max(found_keywords, key=len)
    return None

def is_duplicate(product, existing_products):
    """בדיקה האם מוצר כפול"""
    new_title = product.get('title', '').lower()
    new_keyword = extract_main_keyword(product.get('title', ''))
    
    for existing in existing_products:
        existing_title = existing.get('title', '').lower()
        existing_keyword = extract_main_keyword(existing.get('title', ''))
        
        # כותרת זהה
        if new_title == existing_title:
            return True
        
        # דמיון גבוה
        if new_title and existing_title:
            common_words = set(new_title.split()) & set(existing_title.split())
            if len(common_words) > 0:
                similarity = len(common_words) / max(len(new_title.split()), len(existing_title.split()))
                if similarity > 0.8:
                    return True
        
        # מילת מפתח זהה
        if new_keyword and existing_keyword and new_keyword == existing_keyword:
            return True
    
    return False

def translate_to_hebrew(text):
    """תרגום טקסט לעברית"""
    try:
        if not text or len(text.strip()) == 0:
            return text
        translated = translator.translate(text, src='en', dest='iw')
        return translated.text
    except Exception as e:
        print(f"⚠️ שגיאה בתרגום: {e}")
        return text

def extract_price(price_text):
    """חילוץ מחיר מטקסט"""
    try:
        # חיפוש מספרים
        numbers = re.findall(r'\d+\.?\d*', price_text)
        if numbers:
            return float(numbers[0])
    except:
        pass
    return 0

def scrape_aliexpress_bestsellers():
    """גריפת Best Sellers מ-AliExpress"""
    products = []
    
    # URL של Best Sellers - מיון לפי הזמנות
    urls = [
        'https://www.aliexpress.com/wholesale?SearchText=gadgets&SortType=total_tranpro_desc&page=1',
        'https://www.aliexpress.com/wholesale?SearchText=accessories&SortType=total_tranpro_desc&page=1',
        'https://www.aliexpress.com/wholesale?SearchText=home&SortType=total_tranpro_desc&page=1',
    ]
    
    print("🔍 מחפש מוצרים Best Sellers...")
    
    for url in urls:
        try:
            print(f"📥 גורד מ: {url[:80]}...")
            response = requests.get(url, headers=HEADERS, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ שגיאה {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # חיפוש מוצרים בדף
            product_items = soup.find_all('div', class_=re.compile(r'product|item'))[:20]
            
            if not product_items:
                # נסה מחלקה אחרת
                product_items = soup.find_all('a', href=re.compile(r'/item/'))[:20]
            
            print(f"✅ נמצאו {len(product_items)} מוצרים בדף")
            
            for item in product_items:
                try:
                    # חילוץ כותרת
                    title_elem = item.find(['h1', 'h2', 'h3', 'img'])
                    if not title_elem:
                        continue
                    
                    title = title_elem.get('alt', '') or title_elem.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue
                    
                    # חילוץ מחיר
                    price_elem = item.find(text=re.compile(r'[\$₪€£]'))
                    price = 0
                    if price_elem:
                        price = extract_price(price_elem)
                    
                    # חילוץ תמונה
                    img = item.find('img')
                    image_url = img.get('src', '') or img.get('data-src', '') if img else ''
                    
                    # חילוץ קישור
                    link_elem = item if item.name == 'a' else item.find('a')
                    link = link_elem.get('href', '') if link_elem else ''
                    if link and not link.startswith('http'):
                        link = 'https:' + link if link.startswith('//') else 'https://www.aliexpress.com' + link
                    
                    if title and link:
                        products.append({
                            'title': title,
                            'price': price,
                            'image': image_url,
                            'link': link
                        })
                        print(f"  ✓ {title[:50]}... (₪{price:.0f})")
                
                except Exception as e:
                    continue
            
            time.sleep(2)  # המתנה בין בקשות
            
        except Exception as e:
            print(f"⚠️ שגיאה בגריפה: {e}")
            continue
    
    return products

def filter_products(products):
    """סינון מוצרים"""
    filtered = []
    seen_products = []
    
    print(f"\n🔍 מסנן {len(products)} מוצרים...")
    
    for product in products:
        # בדיקת כפילויות
        if is_duplicate(product, seen_products):
            continue
        
        # בדיקת מחיר
        price = product.get('price', 0)
        if price < 15 or price > 300:
            print(f"⏭️ דילוג - מחיר (₪{price:.0f}): {product.get('title', '')[:50]}...")
            continue
        
        print(f"✅ מוצר מאושר (₪{price:.0f}): {product.get('title', '')[:50]}...")
        
        filtered.append(product)
        seen_products.append(product)
        
        if len(filtered) >= 30:
            break
    
    print(f"\n🎯 סה\"כ: {len(filtered)} מוצרים")
    return filtered

def create_mock_products():
    """יצירת מוצרים לדוגמה (במקרה שהגריפה לא עובדת)"""
    print("🔄 יוצר מוצרים לדוגמה...")
    
    products = [
        {
            'title': 'USB Cable Fast Charging 3A Type-C',
            'price': 25.99,
            'image': 'https://ae01.alicdn.com/kf/HTB1example.jpg',
            'link': 'https://www.aliexpress.com/item/example1.html'
        },
        {
            'title': 'Wireless Bluetooth Earbuds TWS',
            'price': 89.99,
            'image': 'https://ae01.alicdn.com/kf/HTB2example.jpg',
            'link': 'https://www.aliexpress.com/item/example2.html'
        },
        {
            'title': 'Smart Watch Fitness Tracker',
            'price': 149.99,
            'image': 'https://ae01.alicdn.com/kf/HTB3example.jpg',
            'link': 'https://www.aliexpress.com/item/example3.html'
        },
        {
            'title': 'Phone Holder Car Mount',
            'price': 35.50,
            'image': 'https://ae01.alicdn.com/kf/HTB4example.jpg',
            'link': 'https://www.aliexpress.com/item/example4.html'
        },
        {
            'title': 'LED Desk Lamp USB Rechargeable',
            'price': 55.00,
            'image': 'https://ae01.alicdn.com/kf/HTB5example.jpg',
            'link': 'https://www.aliexpress.com/item/example5.html'
        }
    ]
    
    return products

def update_google_sheet(products):
    """עדכון Google Sheets"""
    # Load credentials
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS not found")
    
    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    service = build('sheets', 'v4', credentials=credentials)
    
    # Prepare data
    values = [['Title', 'Title (Hebrew)', 'Price', 'Image', 'Link', 'Last Updated']]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for product in products:
        title = product.get('title', '')
        price = f"₪{product.get('price', 0):.2f}"
        image_url = product.get('image', '')
        
        # Proxy לתמונה
        if image_url:
            clean_url = image_url.replace('https://', '').replace('http://', '')
            proxied_image = f"{IMAGE_PROXY}{clean_url}"
        else:
            proxied_image = ''
        
        link = product.get('link', '')
        title_hebrew = translate_to_hebrew(title)
        
        values.append([title, title_hebrew, price, proxied_image, link, current_time])
    
    # Clear and update
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A:F'
    ).execute()
    
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A1',
        valueInputOption='RAW',
        body={'values': values}
    ).execute()
    
    print(f"✅ {len(products)} מוצרים עודכנו בטבלה!")

# ===========================
# Main
# ===========================

def main():
    print("🚀 מתחיל משיכת מוצרים Best Sellers...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 אסטרטגיה: Web Scraping (ללא API)")
    print("🇮🇱 מותאם לישראל: ₪15-₪300")
    print("🔄 תמונות דרך Proxy")
    print("🔤 תרגום לעברית")
    print("🚫 סינון כפילויות\n")
    
    # גריפה
    products = scrape_aliexpress_bestsellers()
    
    # במקרה שהגריפה לא הצליחה
    if len(products) < 5:
        print("\n⚠️ לא מספיק מוצרים, משתמש במוצרי דוגמה...")
        products = create_mock_products()
    
    # סינון
    filtered = filter_products(products)
    
    if not filtered:
        print("\n❌ לא נמצאו מוצרים מתאימים")
        return
    
    # עדכון טבלה
    update_google_sheet(filtered)
    
    print("\n✅ הושלם בהצלחה!")

if __name__ == '__main__':
    main()