#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from aliexpress_api import AliexpressApi, models

# ===========================
# הגדרות
# ===========================

ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = 'Automation'

SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

# ===========================
# פונקציות
# ===========================

def init_aliexpress_api():
    """אתחול AliExpress API"""
    return AliexpressApi(
        ALIEXPRESS_APP_KEY,
        ALIEXPRESS_APP_SECRET,
        models.Language.EN,
        models.Currency.USD,
        ALIEXPRESS_TRACKING_ID
    )

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
    """הוספת מוצרים לטבלה"""
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
    print(f"🎯 Tracking ID: {ALIEXPRESS_TRACKING_ID}\n")
    
    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("❌ Missing API Keys!")
        return
    
    try:
        # אתחול
        api = init_aliexpress_api()
        print("✅ Connected to AliExpress API\n")
        
        # מוצרים קיימים
        existing_products = get_existing_products()
        
        # חיפוש
        keywords = [
            'phone accessories',
            'smart watch',
            'wireless earbuds',
            'phone case',
            'usb cable'
        ]
        
        all_new = []
        
        for keyword in keywords:
            print(f"🔍 Searching: '{keyword}'...")
            
            try:
                response = api.get_products(
                    keywords=keyword,
                    page_size=20,
                    sort='SALE_PRICE_ASC'
                )
                
                if not response or not hasattr(response, 'products'):
                    print(f"⚠️ No products for '{keyword}'")
                    continue
                
                products = response.products
                print(f"✅ Found {len(products)} products")
                
                for product in products:
                    try:
                        url = product.product_detail_url
                        title = product.product_title
                        
                        if is_duplicate(url, existing_products):
                            continue
                        
                        # Get affiliate link
                        affiliate_links = api.get_affiliate_links([url])
                        affiliate_link = url
                        if affiliate_links and len(affiliate_links) > 0:
                            affiliate_link = affiliate_links[0].promotion_link
                        
                        all_new.append({
                            'url': url,
                            'title': title,
                            'description': url,
                            'image': product.product_main_image_url,
                            'affiliate_link': affiliate_link
                        })
                        
                        existing_products.append({'url': url, 'title': title})
                        
                        print(f"✅ Added: {title[:50]}...")
                        
                        if len(all_new) >= 30:
                            print("\n🎯 Reached 30 products - stopping")
                            break
                        
                        time.sleep(0.3)
                        
                    except Exception as e:
                        continue
                
                if len(all_new) >= 30:
                    break
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error searching '{keyword}': {e}")
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