#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AliExpress to Google Sheets Automation - Affiliate Table Version
כותב ל-Affiliate Table עם 5 עמודות בלבד
"""

import os
import sys
import time
import hashlib
import requests
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import json

# ========== לוגים ==========

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji_map = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "STEP": "🔄"
    }
    emoji = emoji_map.get(level, "📝")
    print(f"[{timestamp}] {emoji} {message}")
    sys.stdout.flush()

# ========== Google Sheets ==========

def connect_to_google_sheets():
    """מתחבר ל-Affiliate Table"""
    try:
        log("מתחבר ל-Google Sheets...", "STEP")
        
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS לא נמצא")
        
        creds_dict = json.loads(creds_json)
        
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID לא נמצא")
        
        spreadsheet = client.open_by_key(sheet_id)
        
        # ========== שינוי: כתיבה ל-Affiliate Table ==========
        try:
            worksheet = spreadsheet.worksheet("Affiliate Table")
            log("התחברנו לטאב: Affiliate Table", "SUCCESS")
        except gspread.exceptions.WorksheetNotFound:
            # אם לא קיים, ניצור אותו
            worksheet = spreadsheet.add_worksheet(title="Affiliate Table", rows="1000", cols="5")
            log("נוצר טאב חדש: Affiliate Table", "SUCCESS")
        
        return worksheet
        
    except Exception as e:
        log(f"שגיאה בהתחברות: {str(e)}", "ERROR")
        raise

# ========== AliExpress API ==========

def generate_signature(app_secret, params):
    sorted_params = sorted(params.items())
    sign_string = app_secret
    for key, value in sorted_params:
        sign_string += str(key) + str(value)
    sign_string += app_secret
    signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
    return signature


def fetch_aliexpress_products(num_products=30):
    """מושך מוצרים עם לינקי אפיליאייט"""
    try:
        log(f"מושך {num_products} מוצרים מ-AliExpress...", "STEP")
        
        app_key = os.environ.get('ALIEXPRESS_APP_KEY')
        app_secret = os.environ.get('ALIEXPRESS_APP_SECRET')
        tracking_id = os.environ.get('ALIEXPRESS_TRACKING_ID')
        
        if not all([app_key, app_secret, tracking_id]):
            raise ValueError("AliExpress credentials חסרים")
        
        timestamp = str(int(time.time() * 1000))
        
        params = {
            'app_key': app_key,
            'method': 'aliexpress.affiliate.product.query',
            'timestamp': timestamp,
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'target_currency': 'USD',
            'target_language': 'EN',
            'tracking_id': tracking_id,
            'page_size': str(num_products),
            'sort': 'SALE_PRICE_ASC',
            'ship_to_country': 'US'
        }
        
        signature = generate_signature(app_secret, params)
        params['sign'] = signature
        
        url = 'https://api-sg.aliexpress.com/sync'
        
        log("שולח בקשה ל-AliExpress API...", "STEP")
        response = requests.get(url, params=params, timeout=30)
        
        log(f"קוד תגובה: {response.status_code}", "INFO")
        
        if response.status_code != 200:
            log(f"שגיאת HTTP: {response.status_code}", "ERROR")
            return []
        
        data = response.json()
        
        if 'error_response' in data:
            error_info = data['error_response']
            log(f"שגיאת API: {error_info.get('msg', 'Unknown')}", "ERROR")
            return []
        
        if 'aliexpress_affiliate_product_query_response' not in data:
            log(f"מבנה תגובה לא צפוי", "ERROR")
            return []
        
        response_data = data['aliexpress_affiliate_product_query_response']
        
        if 'resp_result' not in response_data:
            log("לא נמצא resp_result", "ERROR")
            return []
        
        result = response_data['resp_result']
        
        if 'result' not in result or 'products' not in result['result']:
            log("לא נמצאו מוצרים", "WARNING")
            return []
        
        products = result['result']['products']['product']
        
        log(f"נמשכו {len(products)} מוצרים בהצלחה!", "SUCCESS")
        return products
        
    except Exception as e:
        log(f"שגיאה במשיכת מוצרים: {str(e)}", "ERROR")
        return []


def process_and_write_products(worksheet, products):
    """
    מעבד ומוסיף מוצרים ל-Affiliate Table
    5 עמודות בלבד: PRODUCT_URL | TITLE | DESCRIPTION | IMAGE_URL | AFFILIATE_LINK
    """
    try:
        log(f"מעבד {len(products)} מוצרים...", "STEP")
        
        # ========== בדיקה אם יש כותרות ==========
        existing_data = worksheet.get_all_values()
        
        if not existing_data or existing_data[0] != ['PRODUCT_URL', 'TITLE', 'DESCRIPTION', 'IMAGE_URL', 'AFFILIATE_LINK']:
            # אם אין כותרות, נוסיף אותן
            log("מוסיף כותרות לטבלה...", "STEP")
            worksheet.update('A1:E1', [['PRODUCT_URL', 'TITLE', 'DESCRIPTION', 'IMAGE_URL', 'AFFILIATE_LINK']])
            next_row = 2
        else:
            # מוצא את השורה הריקה הבאה
            next_row = len(existing_data) + 1
        
        log(f"מתחיל לכתוב משורה {next_row}", "INFO")
        
        # ========== מכין נתונים - 5 עמודות בלבד ==========
        rows = []
        
        for product in products:
            try:
                # URL של המוצר המקורי
                product_url = product.get('product_detail_url', 'N/A')
                
                # כותרת
                title = product.get('product_title', 'N/A')
                
                # תיאור - משתמש בכותרת כי AliExpress לא נותן description מלא
                description = product.get('product_title', 'N/A')
                
                # תמונה
                image_url = product.get('product_main_image_url', 'N/A')
                
                # ========== לינק אפיליאייט ==========
                # promotion_link = זה הלינק עם ה-tracking ID שלך!
                affiliate_link = product.get('promotion_link', 'N/A')
                
                # בדיקה שזה לינק אפיליאייט אמיתי
                if affiliate_link == 'N/A' or 'aff_' not in affiliate_link:
                    log(f"אזהרה: מוצר {title[:30]} ללא לינק אפיליאייט תקין", "WARNING")
                
                row = [product_url, title, description, image_url, affiliate_link]
                rows.append(row)
                
            except Exception as e:
                log(f"שגיאה בעיבוד מוצר: {str(e)}", "WARNING")
                continue
        
        # ========== כתיבה לגיליון - מוסיף בסוף! ==========
        if rows:
            log(f"כותב {len(rows)} מוצרים ל-Affiliate Table...", "STEP")
            
            # חישוב הטווח
            start_cell = f'A{next_row}'
            end_cell = f'E{next_row + len(rows) - 1}'
            cell_range = f'{start_cell}:{end_cell}'
            
            worksheet.update(cell_range, rows)
            
            log(f"✅ נוספו {len(rows)} מוצרים לשורות {next_row}-{next_row + len(rows) - 1}!", "SUCCESS")
        else:
            log("לא נמצאו מוצרים לכתיבה", "WARNING")
        
    except Exception as e:
        log(f"שגיאה בכתיבה: {str(e)}", "ERROR")
        raise


def main():
    """פונקציה ראשית"""
    try:
        log("🚀 מתחיל תהליך - Affiliate Table Version", "INFO")
        log("=" * 60, "INFO")
        
        worksheet = connect_to_google_sheets()
        products = fetch_aliexpress_products(num_products=30)
        
        if not products:
            log("לא הצלחנו למשוך מוצרים", "ERROR")
            sys.exit(1)
        
        process_and_write_products(worksheet, products)
        
        log("=" * 60, "INFO")
        log("🎉 התהליך הושלם בהצלחה!", "SUCCESS")
        
    except Exception as e:
        log(f"שגיאה קריטית: {str(e)}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
