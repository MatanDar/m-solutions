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
# הגדרות AliExpress API
# ===========================

ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = 'Automation'

# ===========================
# הגדרות Google Sheets
# ===========================

SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

# ===========================
# אתחול AliExpress API
# ===========================

def init_aliexpress_api():
    """אתחול AliExpress API עם הספרייה המוכנה"""
    return AliexpressApi(
        ALIEXPRESS_APP_KEY,
        ALIEXPRESS_APP_SECRET,
        models.Language.EN,  # עברית לא תמיד נתמכת
        models.Currency.USD,  # ILS לא נתמך - נשתמש ב-USD
        ALIEXPRESS_TRACKING_ID
    )

# ===========================
# פונקציות Google Sheets
# ===========================

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
            if len(row) >= 2:
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
        if existing['url'] in product_url or product_url in existing['url']:
            return True
    return False

def add_products_to_sheet(new_products):
    """הוספת מוצרים חדשים לטבלה"""
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
        
        # Append - הוספה ללא מחיקת קיימים
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
    print("💵 מטבע: USD (ILS לא נתמך)")
    print("➕ מוסיף מוצרים חדשים בלבד (לא מוחק קיימים)\n")
    
    # בדיקת API Keys
    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("❌ חסרים API Keys! בדוק את GitHub Secrets")
        return
    
    try:
        # אתחול API
        api = init_aliexpress_api()
        print("✅ התחברות ל-AliExpress API הצליחה!\n")
        
        # קבלת מוצרים קיימים
        existing_products = get_existing_products()
        
        # חיפוש מוצרים
        search_keywords = [
            'phone accessories',
            'smart gadgets', 
            'wireless earbuds',
            'fitness tracker',
            'usb cable'
        ]
        
        all_new_products = []
        
        for keyword in search_keywords:
            print(f"🔍 מחפש: '{keyword}'...")
            
            try:
                # חיפוש מוצרים
                response = api.get_hotproducts(
                    keywords=keyword,
                    page_size=20
                )
                
                if not response or not hasattr(response, 'products'):
                    print(f"⚠️ לא נמצאו מוצרים עבור '{keyword}'")
                    continue
                
                products = response.products
                print(f"✅ נמצאו {len(products)} מוצרים")
                
                for product in products:
                    try:
                        product_url = product.product_detail_url
                        title = product.product_title
                        
                        # בדיקת כפילויות
                        if is_duplicate(product_url, existing_products):
                            print(f"⏭️ דילוג - קיים: {title[:40]}...")
                            continue
                        
                        # יצירת קישור שותפים
                        print(f"🔗 יוצר קישור affiliate: {title[:40]}...")
                        affiliate_links = api.get_affiliate_links([product_url])
                        
                        affiliate_link = product_url
                        if affiliate_links and len(affiliate_links) > 0:
                            affiliate_link = affiliate_links[0].promotion_link
                        
                        # הוספה לרשימה
                        all_new_products.append({
                            'url': product_url,
                            'title': title,
                            'description': product.product_detail_url,
                            'image': product.product_main_image_url,
                            'affiliate_link': affiliate_link
                        })
                        
                        # הוספה לרשימת קיימים
                        existing_products.append({'url': product_url, 'title': title})
                        
                        print(f"✅ נוסף: {title[:40]}...")
                        
                        # הגבלה ל-30 מוצרים
                        if len(all_new_products) >= 30:
                            print("\n🎯 הגעתי ל-30 מוצרים חדשים - עוצר")
                            break
                        
                        time.sleep(0.3)
                        
                    except Exception as e:
                        print(f"⚠️ שגיאה במוצר: {e}")
                        continue
                
                if len(all_new_products) >= 30:
                    break
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ שגיאה בחיפוש '{keyword}': {e}")
                continue
        
        # הוספת מוצרים לטבלה
        if all_new_products:
            print(f"\n🎉 נמצאו {len(all_new_products)} מוצרים חדשים!")
            add_products_to_sheet(all_new_products)
        else:
            print("\n⚠️ לא נמצאו מוצרים חדשים להוספה")
        
        print("\n✅ הושלם בהצלחה!")
        
    except Exception as e:
        print(f"\n❌ שגיאה כללית: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()