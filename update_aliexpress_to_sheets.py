#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AliExpress to Google Sheets Automation
מערכת אוטומטית למשיכת Best Deals מ-AliExpress וכתיבה ל-Google Sheets
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

# ========== הגדרות ולוגים ==========

def log(message, level="INFO"):
    """פונקציה להדפסת לוגים עם timestamp"""
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

# ========== Google Sheets Connection ==========

def connect_to_google_sheets():
    """מתחבר ל-Google Sheets באמצעות Service Account"""
    try:
        log("מתחבר ל-Google Sheets...", "STEP")
        
        # טוען את ה-credentials מ-Environment Variable
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS לא נמצא ב-Environment Variables")
        
        # ממיר את ה-JSON string לפורמט מילון
        creds_dict = json.loads(creds_json)
        
        # יוצר Credentials object
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        
        # מתחבר ל-gspread
        client = gspread.authorize(credentials)
        
        # פותח את הגיליון
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID לא נמצא ב-Environment Variables")
        
        spreadsheet = client.open_by_key(sheet_id)
        
        # בוחר או יוצר worksheet
        try:
            worksheet = spreadsheet.worksheet("Sheet1")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Sheet1", rows="1000", cols="20")
            log("נוצר worksheet חדש: Sheet1", "SUCCESS")
        
        log(f"התחברנו בהצלחה לגיליון: {spreadsheet.title}", "SUCCESS")
        return worksheet
        
    except Exception as e:
        log(f"שגיאה בהתחברות ל-Google Sheets: {str(e)}", "ERROR")
        raise

# ========== AliExpress API - תיקון החתימה ==========

def generate_signature(app_secret, params):
    """
    יוצר חתימה (signature) לבקשת API של AliExpress
    
    התיקון החשוב:
    - ממיין את הפרמטרים אלפביתית
    - בונה את המחרוזת בפורמט הנכון
    - משתמש ב-MD5 uppercase
    """
    # ממיין את הפרמטרים אלפביתית (זה קריטי!)
    sorted_params = sorted(params.items())
    
    # בונה את המחרוזת לחתימה
    sign_string = app_secret
    for key, value in sorted_params:
        sign_string += str(key) + str(value)
    sign_string += app_secret
    
    # יוצר MD5 hash
    signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
    
    log(f"נבנתה חתימה: {signature[:10]}...", "INFO")
    return signature


def fetch_aliexpress_products(num_products=30):
    """
    מושך Best Deals מ-AliExpress
    
    מה שתוקן:
    - הוספת tracking_id לפרמטרים
    - timestamp במילישניות (13 ספרות)
    - sign_method = "md5" באותיות קטנות
    - סדר אלפביתי של כל הפרמטרים
    """
    try:
        log(f"מושך {num_products} Best Deals מ-AliExpress...", "STEP")
        
        # שולף credentials מ-environment variables
        app_key = os.environ.get('ALIEXPRESS_APP_KEY')
        app_secret = os.environ.get('ALIEXPRESS_APP_SECRET')
        tracking_id = os.environ.get('ALIEXPRESS_TRACKING_ID')
        
        if not all([app_key, app_secret, tracking_id]):
            raise ValueError("AliExpress credentials חסרים ב-Environment Variables")
        
        # ========== תיקון חשוב - הפרמטרים הבסיסיים ==========
        timestamp = str(int(time.time() * 1000))  # מילישניות (13 ספרות)
        
        params = {
            'app_key': app_key,
            'method': 'aliexpress.affiliate.hotproduct.query',
            'timestamp': timestamp,
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',  # ⚠️ באותיות קטנות!
            'target_currency': 'USD',
            'target_language': 'EN',
            'tracking_id': tracking_id,  # ⚠️ חובה להוסיף את זה!
            'page_size': str(num_products)
        }
        
        # ========== יצירת החתימה ==========
        signature = generate_signature(app_secret, params)
        params['sign'] = signature
        
        # ========== שליחת הבקשה ==========
        url = 'https://api-sg.aliexpress.com/sync'
        
        log("שולח בקשה ל-AliExpress API...", "STEP")
        response = requests.get(url, params=params, timeout=30)
        
        log(f"קוד תגובה: {response.status_code}", "INFO")
        
        if response.status_code != 200:
            log(f"שגיאת HTTP: {response.status_code}", "ERROR")
            log(f"תוכן התגובה: {response.text}", "ERROR")
            return []
        
        # ========== ניתוח התגובה ==========
        data = response.json()
        
        # בדיקת שגיאות API
        if 'error_response' in data:
            error_info = data['error_response']
            log(f"שגיאת API: {error_info.get('msg', 'Unknown error')}", "ERROR")
            log(f"קוד שגיאה: {error_info.get('code', 'Unknown')}", "ERROR")
            
            # הצעות לתיקון
            if 'IncompleteSignature' in str(error_info):
                log("💡 נראה שיש בעיה בחתימה. בדוק:", "WARNING")
                log("   1. שה-APP_KEY וה-APP_SECRET נכונים", "WARNING")
                log("   2. שה-TRACKING_ID תואם לזה שב-AliExpress Portal", "WARNING")
            
            return []
        
        # ========== חילוץ המוצרים ==========
        if 'aliexpress_affiliate_hotproduct_query_response' not in data:
            log("לא נמצאה תגובה תקינה מה-API", "ERROR")
            log(f"מבנה התגובה: {list(data.keys())}", "ERROR")
            return []
        
        response_data = data['aliexpress_affiliate_hotproduct_query_response']
        
        if 'resp_result' not in response_data:
            log("לא נמצא resp_result בתגובה", "ERROR")
            return []
        
        result = response_data['resp_result']
        
        if 'result' not in result or 'products' not in result['result']:
            log("לא נמצאו מוצרים בתגובה", "WARNING")
            return []
        
        products = result['result']['products']['product']
        
        log(f"נמשכו {len(products)} מוצרים בהצלחה!", "SUCCESS")
        return products
        
    except requests.exceptions.Timeout:
        log("Timeout - ה-API לא הגיב בזמן", "ERROR")
        return []
    except requests.exceptions.RequestException as e:
        log(f"שגיאת רשת: {str(e)}", "ERROR")
        return []
    except Exception as e:
        log(f"שגיאה כללית במשיכת מוצרים: {str(e)}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        return []


# ========== עיבוד וכתיבה ל-Google Sheets ==========

def process_and_write_products(worksheet, products):
    """מעבד ומעדכן את המוצרים ב-Google Sheets"""
    try:
        log(f"מעבד {len(products)} מוצרים...", "STEP")
        
        # כותרות
        headers = [
            'Name', 'Category', 'Original Price', 'Sale Price', 
            'Discount', 'Rating', 'Sold', 'Shipping', 
            'Image', 'Link', 'Added Date'
        ]
        
        # מכין את הנתונים
        rows = [headers]
        
        for product in products:
            try:
                # חילוץ מידע בסיסי
                name = product.get('product_title', 'N/A')
                category = product.get('first_level_category_name', 'N/A')
                
                # מחירים
                original_price = product.get('original_price', 'N/A')
                sale_price = product.get('sale_price', 'N/A')
                
                # חישוב הנחה
                try:
                    if original_price != 'N/A' and sale_price != 'N/A':
                        discount = round(((float(original_price) - float(sale_price)) / float(original_price)) * 100, 1)
                        discount = f"{discount}%"
                    else:
                        discount = 'N/A'
                except:
                    discount = 'N/A'
                
                # דירוג ומכירות
                rating = product.get('evaluate_rate', 'N/A')
                sold = product.get('volume', 'N/A')
                
                # משלוח
                shipping = "Free Shipping" if product.get('is_free_shipping', False) else "Paid Shipping"
                
                # לינקים
                image_url = product.get('product_main_image_url', '')
                product_url = product.get('promotion_link', '')
                
                # תאריך
                added_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # הוספת שורה
                row = [
                    name, category, original_price, sale_price,
                    discount, rating, sold, shipping,
                    image_url, product_url, added_date
                ]
                
                rows.append(row)
                
            except Exception as e:
                log(f"שגיאה בעיבוד מוצר: {str(e)}", "WARNING")
                continue
        
        # ניקוי ה-worksheet וכתיבת נתונים חדשים
        log("כותב נתונים ל-Google Sheets...", "STEP")
        worksheet.clear()
        worksheet.update('A1', rows)
        
        log(f"נכתבו {len(rows)-1} מוצרים בהצלחה ל-Google Sheets!", "SUCCESS")
        
    except Exception as e:
        log(f"שגיאה בכתיבה ל-Google Sheets: {str(e)}", "ERROR")
        raise


# ========== Main Execution ==========

def main():
    """פונקציה ראשית"""
    try:
        log("🚀 מתחיל תהליך אוטומציה של AliExpress to Google Sheets", "INFO")
        log("=" * 60, "INFO")
        
        # 1. התחברות ל-Google Sheets
        worksheet = connect_to_google_sheets()
        
        # 2. משיכת מוצרים מ-AliExpress
        products = fetch_aliexpress_products(num_products=30)
        
        if not products:
            log("לא הצלחנו למשוך מוצרים מ-AliExpress", "ERROR")
            log("בודק שה-API credentials נכונים ושה-App פעיל", "INFO")
            sys.exit(1)
        
        # 3. עיבוד וכתיבה
        process_and_write_products(worksheet, products)
        
        log("=" * 60, "INFO")
        log("🎉 התהליך הושלם בהצלחה!", "SUCCESS")
        
    except Exception as e:
        log(f"שגיאה קריטית: {str(e)}", "ERROR")
        import traceback
        log(f"Traceback מלא: {traceback.format_exc()}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()