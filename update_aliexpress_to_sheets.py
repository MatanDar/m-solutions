#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import hmac
import hashlib
import requests
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# ===========================
# הגדרות
# ===========================

ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = 'matan123'  # הטראקינג שעבד!

SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

# ===========================
# פונקציות API
# ===========================

def generate_signature(params, secret):
    """
    ✅ החתימה המקורית שעבדה - MD5!
    """
    sorted_params = sorted(params.items())
    sign_string = secret
    for key, value in sorted_params:
        sign_string += f"{key}{value}"
    sign_string += secret
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

def fetch_products():
    """
    ✅ הקוד המקורי שעבד!
    """
    timestamp = str(int(time.time() * 1000))
    
    params = {
        'app_key': str(ALIEXPRESS_APP_KEY),
        'timestamp': str(timestamp),
        'sign_method': 'md5',
        'method': 'aliexpress.affiliate.hotproduct.query',
        'format': 'json',
        'v': '2.0',
        'page_size': '30',
        'page_no': '1',
        'sort': 'SALE_PRICE_ASC',
        'target_currency': 'USD',
        'target_language': 'EN',
        'tracking_id': str(ALIEXPRESS_TRACKING_ID),
    }
    
    params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
    
    # ✅ Gateway המקורי!
    url = "https://api-sg.aliexpress.com/sync"
    
    try:
        print(f"🔍 מבצע קריאה ל-API...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"📦 תשובת API: {json.dumps(data, indent=2)[:500]}...")
        
        if 'aliexpress_affiliate_hotproduct_query_response' in data:
            result = data['aliexpress_affiliate_hotproduct_query_response']['resp_result']
            result_data = json.loads(result['resp_code']) if isinstance(result['resp_code'], str) else result
            
            if result_data.get('resp_code') == 200:
                products = result_data.get('result', {}).get('products', {}).get('product', [])
                print(f"✅ נמצאו {len(products)} מוצרים!")
                return products
            else:
                print(f"❌ שגיאה: {result_data.get('resp_msg', 'Unknown error')}")
                return []
        else:
            print("❌ פורמט תשובה לא צפוי")
            return []
            
    except Exception as e:
        print(f"❌ שגיאה: {str(e)}")
        return []

# ===========================
# פונקציות Google Sheets
# ===========================

def get_existing_products():
    """קבלת מוצרים קיימים"""
    print("📥 טוען מוצרים קיימים...")
    
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:E'
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            return []
        
        existing = []
        for row in values[1:]:
            if len(row) >= 2:
                existing.append({
                    'url': row[0] if len(row) > 0 else '',
                    'title': row[1] if len(row) > 1 else '',
                })
        
        print(f"✅ נמצאו {len(existing)} מוצרים קיימים")
        return existing
        
    except Exception as e:
        print(f"⚠️ שגיאה: {e}")
        return []

def is_duplicate(product_url, existing_products):
    """בדיקת כפילויות"""
    for existing in existing_products:
        if existing['url'] in product_url or product_url in existing['url']:
            return True
    return False

def add_products_to_sheet(new_products):
    """הוספת מוצרים"""
    if not new_products:
        print("⚠️ אין מוצרים להוסיף")
        return
    
    print(f"\n📝 מוסיף {len(new_products)} מוצרים...")
    
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        values = []
        for product in new_products:
            values.append([
                product['url'],
                product['title'],
                product['description'],
                product['image'],
                product['affiliate_link']
            ])
        
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:E',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': values}
        ).execute()
        
        print(f"✅ הוספו {len(new_products)} מוצרים!")
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")

# ===========================
# תהליך ראשי
# ===========================

def main():
    print("🚀 AliExpress Products Updater")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Tracking ID: {ALIEXPRESS_TRACKING_ID}")
    print("✅ שימוש בקוד המקורי שעבד!\n")
    
    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("❌ Missing API Keys!")
        return
    
    try:
        # מוצרים קיימים
        existing_products = get_existing_products()
        
        # משיכת מוצרים
        products = fetch_products()
        
        if not products:
            print("\n⚠️ לא נמצאו מוצרים")
            return
        
        # עיבוד מוצרים
        all_new = []
        
        for product in products:
            try:
                url = product.get('product_detail_url', '')
                title = product.get('product_title', '')
                
                if not url or not title:
                    continue
                
                if is_duplicate(url, existing_products):
                    continue
                
                # קישור affiliate
                promotion_link = product.get('promotion_link', url)
                
                # תמונה
                image = product.get('product_main_image_url', '')
                
                all_new.append({
                    'url': url,
                    'title': title,
                    'description': title[:120],
                    'image': image,
                    'affiliate_link': promotion_link
                })
                
                existing_products.append({'url': url, 'title': title})
                
                print(f"✅ Added: {title[:50]}...")
                
                if len(all_new) >= 30:
                    break
                
            except Exception as e:
                print(f"⚠️ Error: {e}")
                continue
        
        # הוספה לטבלה
        if all_new:
            print(f"\n🎉 Found {len(all_new)} new products!")
            add_products_to_sheet(all_new)
        else:
            print("\n⚠️ No new products found")
        
        print("\n✅ Done!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()