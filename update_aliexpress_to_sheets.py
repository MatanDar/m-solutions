#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AliExpress to Google Sheets Automation - Standard API Version
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

# ========== AliExpress Standard API ==========

def generate_signature(app_secret, params):
    """יוצר חתימה (signature) לבקשת API"""
    sorted_params = sorted(params.items())
    sign_string = app_secret
    for key, value in sorted_params:
        sign_string += str(key) + str(value)
    sign_string += app_secret
    signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
    return signature


def fetch_aliexpress_products(num_products=30):
    """
    מושך מוצרים מ-AliExpress באמצעות Standard API
    משתמש ב-aliexpress.affiliate.product.query (Standard API - Active)
    """
    try:
        log(f"מושך {num_products} מוצרים מ-AliExpress (Standard API)...", "STEP")
        
        app_key = os.environ.get('ALIEXPRESS_APP_KEY')
        app_secret = os.environ.get('ALIEXPRESS_APP_SECRET')
        tracking_id = os.environ.get('ALIEXPRESS_TRACKING_ID')
        
        if not all([app_key, app_secret, tracking_id]):
            raise ValueError("AliExpress credentials חסרים")
        
        timestamp = str(int(time.time() * 1000))
        
        # ========== שימוש ב-Standard API ==========
        params = {
            'app_key': app_key,
            'method': 'aliexpress.affiliate.product.query',  # Standard API
            'timestamp': timestamp,
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'target_currency': 'USD',
            'target_language': 'EN',
            'tracking_id': tracking_id,
            'page_size': str(num_products),
            'sort': 'SALE_PRICE_ASC',  # ממיין לפי מחיר נמוך לגבוה
            'ship_to_country': 'US'
        }
        
        signature = generate_signature(app_secret, params)
        params['sign'] = signature
        
        url = 'https://api-sg.aliexpress.com/sync'
        
        log("שולח בקשה ל-AliExpress Standard API...", "STEP")
        response = requests.get(url, params=params, timeout=30)
        
        log(f"קוד תגובה: {response.status_code}", "INFO")
        
        if response.status_code != 200:
            log(f"שגיאת HTTP: {response.status_code}", "ERROR")
            log(f"תוכן התגובה: {response.text}", "ERROR")
            return []
        
        data = response.json()
        
        # בדיקת שגיאות
        if 'error_response' in data:
            error_info = data['error_response']
            log(f"שגיאת API: {error_info.get('msg', 'Unknown')}", "ERROR")
            log(f"קוד שגיאה: {error_info.get('code', 'Unknown')}", "ERROR")
            return []
        
        # חילוץ מוצרים
        if 'aliexpress_affiliate_product_query_response' not in data:
            log(f"מבנה תגובה לא צפוי: {list(data.keys())}", "ERROR")
            return []
        
        response_data = data['aliexpress_affiliate_product_query_response']
        
        if 'resp_result' not in response_data:
            log("לא נמצא resp_result", "ERROR")
            return []
        
        result = response_data['resp_result']
        
        if 'result' not in result or 'products' not in result['result']:
            log("לא נמצאו מוצרים בתגובה", "WARNING")
            return []
        
        products = result['result']['products']['product']
        
        log(f"נמשכו {len(products)} מוצרים בהצלחה!", "SUCCESS")
        return products
        
    except Exception as e:
        log(f"שגיאה במשיכת מוצרים: {str(e)}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        return []


def process_and_write_products(worksheet, products):
    """מעבד ומעדכן את המוצרים ב-Google Sheets"""
    try:
        log(f"מעבד {len(products)} מוצרים...", "STEP")
        
        headers = [
            'Name', 'Category', 'Original Price', 'Sale Price', 
            'Discount', 'Rating', 'Sold', 'Shipping', 
            'Image', 'Link', 'Added Date'
        ]
        
        rows = [headers]
        
        for product in products:
            try:
                name = product.get('product_title', 'N/A')
                category = product.get('first_level_category_name', 'N/A')
                
                original_price = product.get('original_price', 'N/A')
                sale_price = product.get('sale_price', 'N/A')
                
                try:
                    if original_price != 'N/A' and sale_price != 'N/A':
                        discount = round(((float(original_price) - float(sale_price)) / float(original_price)) * 100, 1)
                        discount = f"{discount}%"
                    else:
                        discount = 'N/A'
                except:
                    discount = 'N/A'
                
                rating = product.get('evaluate_rate', 'N/A')
                sold = product.get('volume', 'N/A')
                shipping = "Free" if product.get('is_free_shipping', False) else "Paid"
                
                image_url = product.get('product_main_image_url', '')
                product_url = product.get('promotion_link', '')
                
                added_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                row = [
                    name, category, original_price, sale_price,
                    discount, rating, sold, shipping,
                    image_url, product_url, added_date
                ]
                
                rows.append(row)
                
            except Exception as e:
                log(f"שגיאה בעיבוד מוצר: {str(e)}", "WARNING")
                continue
        
        log("כותב נתונים ל-Google Sheets...", "STEP")
        worksheet.clear()
        worksheet.update('A1', rows)
        
        log(f"נכתבו {len(rows)-1} מוצרים בהצלחה!", "SUCCESS")
        
    except Exception as e:
        log(f"שגיאה בכתיבה ל-Sheets: {str(e)}", "ERROR")
        raise


def main():
    """פונקציה ראשית"""
    try:
        log("🚀 מתחיל תהליך (Standard API Version)", "INFO")
        log("=" * 60, "INFO")
        
        worksheet = connect_to_google_sheets()
        products = fetch_aliexpress_products(num_products=30)
        
        if not products:
            log("לא הצלחנו למשוך מוצרים", "ERROR")
            log("💡 אם Advanced API עדיין Pending, פתח ticket ב-AliExpress", "WARNING")
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
