import os
import time
import hmac
import hashlib
import requests
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# הגדרות מתוך GitHub Secrets
GOOGLE_SHEETS_CREDENTIALS = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = os.environ.get('ALIEXPRESS_TRACKING_ID')

# קטגוריות מותרות (אלקטרוניקה, אופנה, בית)
ALLOWED_CATEGORIES = [
    '509',  # Electronics
    '1501', # Phones & Accessories
    '200000345', # Computer & Office
    '7', # Women's Clothing
    '200000297', # Men's Clothing
    '1524', # Fashion Accessories
    '13', # Jewelry & Watches
    '15', # Home & Garden
    '6', # Home Improvement
    '1541' # Furniture
]

def generate_signature(params, secret):
    """יצירת חתימה דיגיטלית עבור API Request"""
    sorted_params = sorted(params.items())
    sign_string = secret
    for key, value in sorted_params:
        sign_string += f"{key}{value}"
    sign_string += secret
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

def fetch_hot_products():
    """משיכת מוצרים חמים (HOT PRODUCTS) מ-AliExpress"""
    timestamp = str(int(time.time() * 1000))
    
    params = {
        'app_key': ALIEXPRESS_APP_KEY,
        'timestamp': timestamp,
        'sign_method': 'md5',
        'method': 'aliexpress.affiliate.hotproduct.query',
        'format': 'json',
        'v': '2.0',
        'page_size': '30',
        'page_no': '1',
        'sort': 'SALE_PRICE_ASC',
        'target_currency': 'USD',
        'target_language': 'EN',
        'tracking_id': ALIEXPRESS_TRACKING_ID,
        'category_ids': ','.join(ALLOWED_CATEGORIES)
    }
    
    params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
    
    url = "https://api-sg.aliexpress.com/sync"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"API Response: {json.dumps(data, indent=2)}")
        
        if 'aliexpress_affiliate_hotproduct_query_response' in data:
            result = data['aliexpress_affiliate_hotproduct_query_response']['resp_result']
            result_data = json.loads(result['resp_code']) if isinstance(result['resp_code'], str) else result
            
            if result_data.get('resp_code') == 200:
                products = result_data.get('result', {}).get('products', {}).get('product', [])
                print(f"✅ נמצאו {len(products)} מוצרים חמים!")
                return products
            else:
                print(f"❌ שגיאה: {result_data.get('resp_msg', 'Unknown error')}")
                return []
        else:
            print("❌ פורמט תשובה לא צפוי מה-API")
            return []
            
    except Exception as e:
        print(f"❌ שגיאה במשיכת מוצרים: {str(e)}")
        return []

def get_clean_image_url(product):
    """מקבל URL תמונה נקי ועובד"""
    # נסה למצוא את התמונה הטובה ביותר
    image_url = product.get('product_main_image_url', '')
    
    # אם אין תמונה ראשית, נסה תמונות קטנות
    if not image_url:
        image_url = product.get('product_small_image_urls', {}).get('string', [''])[0] if product.get('product_small_image_urls') else ''
    
    # נקה את ה-URL - הסר פרמטרים מיותרים
    if image_url and '?' in image_url:
        image_url = image_url.split('?')[0]
    
    # ודא שיש פרוטוקול
    if image_url and not image_url.startswith('http'):
        image_url = 'https:' + image_url if image_url.startswith('//') else 'https://' + image_url
    
    return image_url if image_url else 'NO_IMAGE'

def get_product_description(product):
    """מקבל תיאור המוצר - לא URL של תמונה!"""
    # נסה למצוא תיאור אמיתי
    title = product.get('product_title', 'No Description')
    
    # אם יש second_level_category_name, נשתמש בו כתיאור
    category = product.get('second_level_category_name', '')
    if category:
        return f"{category} - {title[:50]}"  # 50 תווים ראשונים מהכותרת
    
    # אחרת, רק הכותרת
    return title[:100]  # 100 תווים ראשונים

def write_to_google_sheets(products):
    """כתיבת מוצרים ל-Google Sheets"""
    try:
        credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        sheet_name = "Affiliate Table"
        
        result = sheet.values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A:F"
        ).execute()
        
        existing_data = result.get('values', [])
        
        if not existing_data:
            headers = [['PRODUCT_URL', 'TITLE', 'DESCRIPTION', 'IMAGE_URL', 'AFFILIATE_LINK', 'RATING']]
            sheet.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"{sheet_name}!A1:F1",
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            existing_data = headers
        
        next_row = len(existing_data) + 1
        
        new_rows = []
        for product in products:
            # לינק אפיליאייט אמיתי
            promotion_link = product.get('promotion_link', '')
            if not promotion_link and product.get('product_detail_url'):
                promotion_link = f"{product['product_detail_url']}?aff_trace_key={ALIEXPRESS_TRACKING_ID}"
            
            # דירוג
            rating = product.get('evaluate_rate', 'N/A')
            if rating and rating != 'N/A':
                try:
                    rating = f"{float(rating):.1f}★"
                except:
                    rating = 'N/A'
            
            # ✅ תיקון הבעיה! עמודה C = DESCRIPTION (לא תמונה!)
            row = [
                product.get('product_detail_url', ''),                # A: PRODUCT_URL
                product.get('product_title', 'No Title'),             # B: TITLE
                get_product_description(product),                     # C: DESCRIPTION ← תוקן!
                get_clean_image_url(product),                         # D: IMAGE_URL ← שופר!
                promotion_link,                                        # E: AFFILIATE_LINK
                rating                                                 # F: RATING
            ]
            new_rows.append(row)
        
        if new_rows:
            sheet.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"{sheet_name}!A{next_row}:F{next_row + len(new_rows) - 1}",
                valueInputOption='RAW',
                body={'values': new_rows}
            ).execute()
            
            print(f"✅ {len(new_rows)} מוצרים חמים נכתבו ל-Google Sheets בהצלחה!")
        else:
            print("⚠️ לא נמצאו מוצרים לכתיבה")
            
    except Exception as e:
        print(f"❌ שגיאה בכתיבה ל-Google Sheets: {str(e)}")

def main():
    print("🚀 מתחיל משיכת מוצרים חמים מ-AliExpress...")
    print(f"📅 תאריך: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 קטגוריות: אלקטרוניקה, אופנה, בית")
    
    products = fetch_hot_products()
    
    if products:
        write_to_google_sheets(products)
        print("✅ הריצה הסתיימה בהצלחה!")
    else:
        print("⚠️ לא נמצאו מוצרים")

if __name__ == "__main__":
    main()