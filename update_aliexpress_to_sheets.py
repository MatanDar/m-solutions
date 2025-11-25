#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AliExpress to Google Sheets Automation
======================================
מערכת אוטומטית שמושכת Best Deals מ-AliExpress 
וכותבת אותם ישירות ל-Google Sheets

Author: Claude + Matan
Date: November 2024
"""

import os
import sys
import json
import time
import hashlib
import hmac
from datetime import datetime
from urllib.parse import quote
import requests
import gspread
from google.oauth2.service_account import Credentials

# ============================================
# הגדרות Google Sheets
# ============================================

GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ============================================
# הגדרות AliExpress API
# ============================================

ALIEXPRESS_API_URL = "https://api-sg.aliexpress.com/sync"
API_METHOD = "aliexpress.affiliate.hotproduct.query"

# ============================================
# פונקציות עזר
# ============================================

def log(message, level="INFO"):
    """
    מדפיס הודעת לוג עם חותמת זמן
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    emoji = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "PROGRESS": "🔄"
    }.get(level, "📝")
    
    print(f"[{timestamp}] {emoji} {message}")
    sys.stdout.flush()

def get_env_variable(var_name, required=True):
    """
    מושך משתנה מה-environment variables
    """
    value = os.environ.get(var_name)
    if required and not value:
        log(f"Missing required environment variable: {var_name}", "ERROR")
        sys.exit(1)
    return value

# ============================================
# חיבור ל-Google Sheets
# ============================================

def connect_to_google_sheets():
    """
    מתחבר ל-Google Sheets דרך Service Account
    Returns: worksheet object
    """
    log("מתחבר ל-Google Sheets...", "PROGRESS")
    
    try:
        # קריאת credentials
        creds_json = get_env_variable('GOOGLE_SHEETS_CREDENTIALS')
        sheet_id = get_env_variable('GOOGLE_SHEET_ID')
        
        # המרת JSON string ל-dictionary
        creds_dict = json.loads(creds_json)
        
        # יצירת credentials
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=GOOGLE_SCOPES
        )
        
        # התחברות ל-gspread
        client = gspread.authorize(credentials)
        
        # פתיחת הגיליון
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.sheet1  # הטאב הראשון
        
        log(f"התחברנו בהצלחה לגיליון: {spreadsheet.title}", "SUCCESS")
        
        return worksheet
        
    except json.JSONDecodeError as e:
        log(f"שגיאה בפענוח JSON של credentials: {e}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"שגיאה בחיבור ל-Google Sheets: {e}", "ERROR")
        sys.exit(1)

# ============================================
# AliExpress API - חתימה
# ============================================

def create_signature(params, app_secret):
    """
    יוצר חתימה לבקשת AliExpress API
    AliExpress משתמש ב-HMAC-MD5 signature
    
    Args:
        params: dictionary של פרמטרים
        app_secret: ה-APP_SECRET מ-AliExpress
    
    Returns:
        signature string
    """
    # ממיין את הפרמטרים לפי ABC
    sorted_params = sorted(params.items())
    
    # יוצר string מהפרמטרים
    param_string = "".join([f"{k}{v}" for k, v in sorted_params])
    
    # יוצר את ה-signature עם HMAC-MD5
    sign = hmac.new(
        app_secret.encode('utf-8'),
        param_string.encode('utf-8'),
        hashlib.md5
    ).hexdigest().upper()
    
    return sign

# ============================================
# AliExpress API - משיכת מוצרים
# ============================================

def fetch_best_deals_from_aliexpress(limit=30):
    """
    מושך Best Deals מ-AliExpress API
    
    Args:
        limit: מספר מוצרים למשוך (ברירת מחדל: 30)
    
    Returns:
        list של מוצרים או None במקרה של שגיאה
    """
    log(f"מושך {limit} Best Deals מ-AliExpress...", "PROGRESS")
    
    try:
        # קריאת credentials
        app_key = get_env_variable('ALIEXPRESS_APP_KEY')
        app_secret = get_env_variable('ALIEXPRESS_APP_SECRET')
        tracking_id = get_env_variable('ALIEXPRESS_TRACKING_ID')
        
        # בניית הפרמטרים
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        params = {
            "app_key": app_key,
            "method": API_METHOD,
            "timestamp": timestamp,
            "format": "json",
            "v": "2.0",
            "sign_method": "md5",
            "tracking_id": tracking_id,
            "fields": "commission_rate,sale_price,original_price,discount,product_title,product_id,product_main_image_url,product_video_url,product_small_image_urls,platform_product_type,shop_url,promo_code_info",
            "sort": "SALE_PRICE_ASC",  # ממיין לפי מחיר עולה
            "page_size": str(limit),
            "page_no": "1",
            "target_currency": "USD",
            "target_language": "EN"
        }
        
        # יצירת חתימה
        signature = create_signature(params, app_secret)
        params["sign"] = signature
        
        log("שולח בקשה ל-AliExpress API...", "PROGRESS")
        
        # שליחת הבקשה
        response = requests.get(ALIEXPRESS_API_URL, params=params, timeout=30)
        
        log(f"קוד תגובה: {response.status_code}", "INFO")
        
        if response.status_code != 200:
            log(f"שגיאה בבקשה: Status {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            return None
        
        # פענוח התגובה
        data = response.json()
        
        # בדיקה אם יש שגיאה
        if "error_response" in data:
            error = data["error_response"]
            log(f"שגיאת API: {error.get('msg', 'Unknown error')}", "ERROR")
            log(f"קוד שגיאה: {error.get('code', 'N/A')}", "ERROR")
            return None
        
        # חילוץ המוצרים
        if API_METHOD.replace(".", "_") + "_response" in data:
            response_key = API_METHOD.replace(".", "_") + "_response"
            result = data[response_key].get("result", {})
            products = result.get("products", {}).get("product", [])
            
            if products:
                log(f"נמצאו {len(products)} מוצרים!", "SUCCESS")
                return products
            else:
                log("לא נמצאו מוצרים", "WARNING")
                return []
        else:
            log("פורמט תגובה לא צפוי מ-API", "ERROR")
            log(f"Response keys: {list(data.keys())}", "ERROR")
            return None
            
    except requests.exceptions.Timeout:
        log("הבקשה ל-API לקחה יותר מדי זמן (timeout)", "ERROR")
        return None
    except requests.exceptions.RequestException as e:
        log(f"שגיאה בבקשת HTTP: {e}", "ERROR")
        return None
    except json.JSONDecodeError as e:
        log(f"שגיאה בפענוח JSON: {e}", "ERROR")
        return None
    except Exception as e:
        log(f"שגיאה לא צפויה: {e}", "ERROR")
        return None

# ============================================
# עיבוד מוצרים
# ============================================

def process_product(product):
    """
    מעבד מוצר בודד ומחזיר אותו בפורמט נקי
    
    Args:
        product: מוצר מה-API
    
    Returns:
        dictionary עם פרטי המוצר
    """
    try:
        # חילוץ מחירים
        original_price = float(product.get('original_price', 0))
        sale_price = float(product.get('sale_price', 0))
        
        # חישוב אחוז הנחה
        if original_price > 0:
            discount_percent = int(((original_price - sale_price) / original_price) * 100)
        else:
            discount_percent = 0
        
        # חילוץ תמונה ראשית
        image_url = product.get('product_main_image_url', '')
        if not image_url:
            small_images = product.get('product_small_image_urls', {}).get('string', [])
            if small_images:
                image_url = small_images[0] if isinstance(small_images, list) else small_images
        
        # בניית לינק affiliate
        product_id = product.get('product_id', '')
        tracking_id = get_env_variable('ALIEXPRESS_TRACKING_ID', required=False) or 'default'
        affiliate_link = f"https://www.aliexpress.com/item/{product_id}.html?aff_fcid=&aff_fsk=&aff_platform=&aff_trace_key={tracking_id}"
        
        # חילוץ קטגוריה
        category = product.get('first_level_category_name', 'General')
        
        return {
            'name': product.get('product_title', 'No Title'),
            'category': category,
            'original_price': f"${original_price:.2f}",
            'sale_price': f"${sale_price:.2f}",
            'discount': f"{discount_percent}%",
            'rating': product.get('evaluate_rate', 'N/A'),
            'sold': product.get('volume', '0'),
            'shipping': 'Free Shipping' if product.get('is_free_shipping', False) else 'Paid Shipping',
            'image': image_url,
            'link': affiliate_link,
            'added_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    except Exception as e:
        log(f"שגיאה בעיבוד מוצר: {e}", "WARNING")
        return None

# ============================================
# כתיבה ל-Google Sheets
# ============================================

def write_products_to_sheet(worksheet, products):
    """
    כותב מוצרים ל-Google Sheets
    
    Args:
        worksheet: אובייקט worksheet של gspread
        products: רשימת מוצרים לכתוב
    
    Returns:
        מספר המוצרים שנכתבו
    """
    log(f"כותב {len(products)} מוצרים ל-Google Sheets...", "PROGRESS")
    
    try:
        # בדיקה אם יש כותרות
        try:
            existing_data = worksheet.get_all_values()
            has_headers = len(existing_data) > 0 and existing_data[0]
        except:
            has_headers = False
        
        # אם אין כותרות, נוסיף
        if not has_headers:
            headers = [
                "Name",
                "Category",
                "Original Price",
                "Sale Price",
                "Discount",
                "Rating",
                "Sold",
                "Shipping",
                "Image",
                "Link",
                "Added Date"
            ]
            worksheet.append_row(headers)
            log("הוספנו שורת כותרות", "INFO")
        
        # הוספת המוצרים
        rows_added = 0
        for product in products:
            if product:  # רק אם המוצר תקין
                row = [
                    product['name'],
                    product['category'],
                    product['original_price'],
                    product['sale_price'],
                    product['discount'],
                    str(product['rating']),
                    str(product['sold']),
                    product['shipping'],
                    product['image'],
                    product['link'],
                    product['added_date']
                ]
                worksheet.append_row(row)
                rows_added += 1
                
                # המתנה קטנה בין שורות למנוע rate limiting
                time.sleep(0.5)
        
        log(f"נכתבו {rows_added} מוצרים בהצלחה!", "SUCCESS")
        return rows_added
        
    except Exception as e:
        log(f"שגיאה בכתיבה ל-Google Sheets: {e}", "ERROR")
        return 0

# ============================================
# פונקציה ראשית
# ============================================

def main():
    """
    הפונקציה הראשית של התוכנית
    """
    log("🚀 מתחיל תהליך אוטומציה של AliExpress to Google Sheets", "INFO")
    log("=" * 60, "INFO")
    
    # שלב 1: התחברות ל-Google Sheets
    worksheet = connect_to_google_sheets()
    
    # שלב 2: משיכת מוצרים מ-AliExpress
    raw_products = fetch_best_deals_from_aliexpress(limit=30)
    
    if not raw_products:
        log("לא הצלחנו למשוך מוצרים מ-AliExpress", "ERROR")
        log("בודק שה-API credentials נכונים ושה-App פעיל", "INFO")
        sys.exit(1)
    
    # שלב 3: עיבוד המוצרים
    log("מעבד את המוצרים...", "PROGRESS")
    processed_products = []
    for product in raw_products:
        processed = process_product(product)
        if processed:
            processed_products.append(processed)
    
    log(f"עובדו {len(processed_products)} מוצרים בהצלחה", "SUCCESS")
    
    # שלב 4: כתיבה ל-Google Sheets
    if processed_products:
        rows_added = write_products_to_sheet(worksheet, processed_products)
        
        if rows_added > 0:
            log("=" * 60, "INFO")
            log(f"✅ התהליך הושלם בהצלחה! נוספו {rows_added} מוצרים חדשים", "SUCCESS")
            log("=" * 60, "INFO")
        else:
            log("לא נוספו מוצרים חדשים", "WARNING")
    else:
        log("אין מוצרים לכתוב", "WARNING")

# ============================================
# הרצת התוכנית
# ============================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nהתהליך הופסק על ידי המשתמש", "WARNING")
        sys.exit(0)
    except Exception as e:
        log(f"שגיאה קריטית: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)