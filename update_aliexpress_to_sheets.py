#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import hashlib
import hmac
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from urllib.parse import quote

# ===========================
# הגדרות AliExpress API
# ===========================

ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = 'Automation'  # ה-Tracking ID החדש שיצרת

API_GATEWAY = 'https://api-sg.aliexpress.com/sync'

# ===========================
# הגדרות Google Sheets
# ===========================

SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

# ===========================
# פונקציות עזר
# ===========================

def generate_signature(params, secret):
    """יצירת חתימה ל-API"""
    # מיון הפרמטרים לפי ABC
    sorted_params = sorted(params.items())
    
    # יצירת מחרוזת
    sign_string = secret
    for key, value in sorted_params:
        sign_string += f"{key}{value}"
    sign_string += secret
    
    # חישוב HMAC-SHA256
    signature = hmac.new(
        secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    
    return signature

def call_aliexpress_api(method, params=None):
    """קריאה ל-AliExpress API"""
    if params is None:
        params = {}
    
    # פרמטרים בסיסיים
    base_params = {
        'app_key': ALIEXPRESS_APP_KEY,
        'method': method,
        'timestamp': str(int(time.time() * 1000)),
        'format': 'json',
        'v': '2.0',
        'sign_method': 'sha256',
    }
    
    # שילוב עם פרמטרים נוספים
    all_params = {**base_params, **params}
    
    # יצירת חתימה
    signature = generate_signature(all_params, ALIEXPRESS_APP_SECRET)
    all_params['sign'] = signature
    
    # שליחת בקשה
    try:
        response = requests.post(API_GATEWAY, data=all_params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ שגיאת API: {e}")
        return None

def search_products(keywords, page=1, page_size=50):
    """חיפוש מוצרים ב-AliExpress"""
    print(f"🔍 מחפש מוצרים: '{keywords}' (עמוד {page})...")
    
    params = {
        'keywords': keywords,
        'page_no': str(page),
        'page_size': str(page_size),
        'target_currency': 'ILS',
        'target_language': 'HE',
        'ship_to_country': 'IL',
        'sort': 'SALE_PRICE_ASC',  # מיון לפי מחיר עולה
        'tracking_id': ALIEXPRESS_TRACKING_ID,
    }
    
    result = call_aliexpress_api('aliexpress.affiliate.hotproduct.query', params)
    
    if not result:
        print("❌ לא התקבלה תשובה מה-API")
        return []
    
    # בדיקת שגיאות
    if 'error_response' in result:
        print(f"❌ שגיאת API: {result['error_response']}")
        return []
    
    # חילוץ מוצרים
    try:
        products = result.get('aliexpress_affiliate_hotproduct_query_response', {}).get('result', {}).get('products', {}).get('product', [])
        print(f"✅ נמצאו {len(products)} מוצרים")
        return products
    except Exception as e:
        print(f"❌ שגיאה בחילוץ מוצרים: {e}")
        return []

def generate_affiliate_link(product_url):
    """יצירת קישור שותפים"""
    params = {
        'promotion_link_type': '0',
        'source_values': product_url,
        'tracking_id': ALIEXPRESS_TRACKING_ID,
    }
    
    result = call_aliexpress_api('aliexpress.affiliate.link.generate', params)
    
    if not result or 'error_response' in result:
        return product_url  # אם נכשל, נחזיר את הקישור המקורי
    
    try:
        links = result.get('aliexpress_affiliate_link_generate_response', {}).get('result', {}).get('promotion_links', {}).get('promotion_link', [])
        if links and len(links) > 0:
            return links[0].get('promotion_link', product_url)
    except:
        pass
    
    return product_url

def get_existing_products():
    """קבלת מוצרים קיימים מהטבלה"""
    print("📥 טוען מוצרים קיימים מהטבלה...")
    
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # קריאת הטבלה
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:E'
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            print("✅ הטבלה ריקה או יש רק כותרות")
            return []
        
        # דילוג על שורת כותרות
        existing = []
        for row in values[1:]:
            if len(row) >= 2:  # לפחות URL ו-Title
                existing.append({
                    'url': row[0] if len(row) > 0 else '',
                    'title': row[1] if len(row) > 1 else '',
                })
        
        print(f"✅ נמצאו {len(existing)} מוצרים קיימים")
        return existing
        
    except Exception as e:
        print(f"⚠️ שגיאה בקריאת טבלה: {e}")
        return []

def is_duplicate(product_url, existing_products):
    """בדיקה אם מוצר כבר קיים"""
    for existing in existing_products:
        if existing['url'] == product_url:
            return True
    return False

def add_products_to_sheet(new_products):
    """הוספת מוצרים חדשים לטבלה (ללא מחיקת קיימים)"""
    if not new_products:
        print("⚠️ אין מוצרים חדשים להוסיף")
        return
    
    print(f"\n📝 מוסיף {len(new_products)} מוצרים חדשים לטבלה...")
    
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # הוספה בסוף הטבלה
        values = []
        for product in new_products:
            values.append([
                product['url'],
                product['title'],
                product['description'],
                product['image'],
                product['affiliate_link']
            ])
        
        # Append (הוספה) ולא Update (עדכון)
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:E',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': values}
        ).execute()
        
        print(f"✅ הוספו {len(new_products)} מוצרים בהצלחה!")
        
    except Exception as e:
        print(f"❌ שגיאה בהוספת מוצרים: {e}")

# ===========================
# תהליך ראשי
# ===========================

def main():
    print("🚀 מתחיל תהליך עדכון מוצרים AliExpress")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Tracking ID: {ALIEXPRESS_TRACKING_ID}")
    print("🇮🇱 מותאם לישראל (ILS, HE, IL)")
    print("➕ מוסיף מוצרים חדשים בלבד (לא מוחק קיימים)\n")
    
    # בדיקת API Keys
    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("❌ חסרים API Keys! בדוק את GitHub Secrets")
        return
    
    # 1. קבלת מוצרים קיימים
    existing_products = get_existing_products()
    
    # 2. חיפוש מוצרים חדשים
    search_keywords = [
        'phone accessories',
        'smart gadgets',
        'home decor',
        'fitness tracker',
        'wireless earbuds',
    ]
    
    all_new_products = []
    
    for keyword in search_keywords:
        products = search_products(keyword, page=1, page_size=20)
        
        for product in products:
            try:
                # חילוץ נתונים
                product_id = product.get('product_id', '')
                product_url = f"https://www.aliexpress.com/item/{product_id}.html"
                title = product.get('product_title', 'No Title')
                
                # בדיקת כפילויות
                if is_duplicate(product_url, existing_products):
                    print(f"⏭️ דילוג - מוצר כבר קיים: {title[:50]}...")
                    continue
                
                # יצירת קישור שותפים
                print(f"🔗 יוצר קישור שותפים עבור: {title[:50]}...")
                affiliate_link = generate_affiliate_link(product_url)
                
                # הוספה לרשימה
                all_new_products.append({
                    'url': product_url,
                    'title': title,
                    'description': product.get('product_detail_url', ''),
                    'image': product.get('product_main_image_url', ''),
                    'affiliate_link': affiliate_link
                })
                
                # הוספה לרשימת קיימים כדי למנוע כפילויות בתוך הריצה
                existing_products.append({'url': product_url, 'title': title})
                
                # הגבלה ל-30 מוצרים חדשים
                if len(all_new_products) >= 30:
                    print("🎯 הגעתי ל-30 מוצרים חדשים - עוצר")
                    break
                
                # Delay קטן בין קריאות
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ שגיאה בעיבוד מוצר: {e}")
                continue
        
        if len(all_new_products) >= 30:
            break
        
        # Delay בין חיפושים
        time.sleep(1)
    
    # 3. הוספת מוצרים חדשים לטבלה
    if all_new_products:
        print(f"\n🎉 נמצאו {len(all_new_products)} מוצרים חדשים!")
        add_products_to_sheet(all_new_products)
    else:
        print("\n⚠️ לא נמצאו מוצרים חדשים להוספה")
    
    print("\n✅ הושלם בהצלחה!")

if __name__ == '__main__':
    main()