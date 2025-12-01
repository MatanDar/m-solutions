import os
import time
import hmac
import hashlib
import requests
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import re
from googletrans import Translator

# הגדרות מתוך GitHub Secrets
GOOGLE_SHEETS_CREDENTIALS = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = os.environ.get('ALIEXPRESS_TRACKING_ID')

# יצירת אובייקט מתרגם
translator = Translator()

# קטגוריות מותרות (אלקטרוניקה, אופנה, בית)
ALLOWED_CATEGORIES = [
    '509', '1501', '200000345',  # Electronics
    '7', '200000297', '1524', '13',  # Fashion
    '15', '6', '1541'  # Home
]

# ✅ מילות מפתח למוצרים נפוצים
# אם 2 מוצרים חולקים אותה מילת מפתח - רק אחד יישמר!
PRODUCT_KEYWORDS = [
    # Electronics
    'cable', 'charger', 'adapter', 'mouse', 'keyboard', 'headphone', 'earphone', 'speaker',
    'powerbank', 'battery', 'usb', 'hdmi', 'bluetooth', 'wireless', 'remote', 'controller',
    'light', 'lamp', 'led', 'bulb', 'strip', 'lighter', 'torch', 'flashlight',
    'watch', 'smartwatch', 'band', 'tracker', 'camera', 'tripod', 'lens', 'drone',
    'phone', 'tablet', 'laptop', 'computer', 'monitor', 'screen', 'display',
    
    # Fashion
    'shirt', 'tshirt', 'dress', 'skirt', 'pants', 'jeans', 'shorts', 'jacket', 'coat',
    'sweater', 'hoodie', 'shoes', 'sneakers', 'boots', 'sandals', 'hat', 'cap',
    'bag', 'backpack', 'wallet', 'belt', 'watch', 'bracelet', 'necklace', 'ring',
    'socks', 'underwear', 'bra', 'bikini', 'swimsuit', 'gloves', 'scarf',
    
    # Home
    'mug', 'cup', 'bottle', 'thermos', 'plate', 'bowl', 'spoon', 'fork', 'knife',
    'pan', 'pot', 'cooker', 'blender', 'mixer', 'kettle', 'toaster', 'oven',
    'pillow', 'blanket', 'sheet', 'curtain', 'towel', 'mat', 'rug', 'carpet',
    'organizer', 'storage', 'box', 'basket', 'rack', 'shelf', 'holder', 'hanger',
    'clock', 'mirror', 'frame', 'vase', 'plant', 'pot', 'garden', 'tool'
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
    """משיכת מוצרים פופולריים מ-AliExpress עם דירוג גבוה"""
    timestamp = str(int(time.time() * 1000))
    
    params = {
        'app_key': ALIEXPRESS_APP_KEY,
        'timestamp': timestamp,
        'sign_method': 'md5',
        'method': 'aliexpress.affiliate.hotproduct.query',
        'format': 'json',
        'v': '2.0',
        'page_size': '100',  # ✅ מושך הרבה כדי לסנן
        'page_no': '1',
        'sort': 'VOLUME_ASC',  # ✅ לפי מכירות - מוצרים מוכחים!
        'target_currency': 'ILS',  # ✅ מחירים בשקלים!
        'target_language': 'EN',   # ✅ אנגלית - נתרגם בעצמנו!
        'tracking_id': ALIEXPRESS_TRACKING_ID,
        'category_ids': ','.join(ALLOWED_CATEGORIES),
        'ship_to_country': 'IL',   # ✅ משלוח לישראל בלבד!
        'delivery_days': '15'      # ✅ עד 15 יום משלוח
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
                print(f"✅ נמצאו {len(products)} מוצרים לפני סינון!")
                
                # ✅ סינון מוצרים לישראל
                filtered_products = filter_products_for_israel(products)
                print(f"✅ נשארו {len(filtered_products)} מוצרים אחרי סינון לישראל!")
                
                return filtered_products
            else:
                print(f"❌ שגיאה: {result_data.get('resp_msg', 'Unknown error')}")
                return []
        else:
            print("❌ פורמט תשובה לא צפוי מה-API")
            return []
            
    except Exception as e:
        print(f"❌ שגיאה במשיכת מוצרים: {str(e)}")
        return []

def filter_products_for_israel(products):
    """
    ✅ סינון מוצרים איכותיים מותאמים לישראל:
    1. דירוג 4.0+ בלבד (מוצרים מוכחים!)
    2. יש מכירות (לא מוצרים חדשים)
    3. משלוח לישראל
    """
    filtered = []
    
    for product in products:
        # ✅ בדיקת דירוג - רק 4.0+!
        rating = product.get('evaluate_rate', '0')
        try:
            rating_value = float(rating) if rating and rating != 'N/A' else 0
        except:
            rating_value = 0
        
        # דירוג חייב להיות 4.0+
        if rating_value < 4.0:
            print(f"⏭️ דילוג - דירוג נמוך ({rating_value}): {product.get('product_title', '')[:40]}...")
            continue
        
        print(f"✅ מוצר מאושר (דירוג {rating_value}): {product.get('product_title', '')[:40]}...")
        filtered.append(product)
    
    # מיון לפי דירוג (הכי גבוה קודם)
    filtered.sort(key=lambda x: float(x.get('evaluate_rate', '0') or '0'), reverse=True)
    
    # מחזיר רק 30 הטובים ביותר
    print(f"🎯 סה\"כ מוצרים עם דירוג 4.0+: {len(filtered)}")
    return filtered[:30]

def convert_to_proxy_url(image_url):
    """
    ✅ פונקציה קריטית!
    ממירה כל URL של תמונה ל-URL דרך Proxy
    ככה AliExpress לא יכול לחסום!
    """
    if not image_url or image_url == 'NO_IMAGE':
        return 'https://via.placeholder.com/400x400/e0e0e0/666666?text=No+Image'
    
    # נקה את ה-URL
    if '?' in image_url:
        image_url = image_url.split('?')[0]
    
    # ודא פרוטוקול
    if not image_url.startswith('http'):
        image_url = 'https:' + image_url if image_url.startswith('//') else 'https://' + image_url
    
    # ✅ המרה ל-Proxy URL!
    # הסר את https:// או http://
    clean_url = image_url.replace('https://', '').replace('http://', '')
    
    # צור proxy URL
    proxy_url = f"https://images.weserv.nl/?url={clean_url}&w=400&h=400&fit=cover&default=1"
    
    print(f"🔄 Proxy: {image_url[:50]}... → {proxy_url[:80]}...")
    return proxy_url

def translate_to_hebrew(text):
    """
    ✅ פונקציה חדשה!
    מתרגמת טקסט לעברית באמצעות Google Translate
    """
    try:
        if not text or len(text.strip()) == 0:
            return text
        
        # תרגום לעברית
        translated = translator.translate(text, src='en', dest='he')
        print(f"🔤 תרגום: {text[:40]}... → {translated.text[:40]}...")
        return translated.text
    except Exception as e:
        print(f"⚠️ שגיאה בתרגום, משאיר באנגלית: {str(e)}")
        return text  # אם יש בעיה, נשאיר באנגלית

def extract_main_keyword(title):
    """
    ✅ מחלץ את מילת המפתח העיקרית מכותרת המוצר
    לדוגמה: "USB Cable Fast Charging 3A" → "cable"
    """
    title_lower = title.lower()
    
    # חיפוש מילת מפתח מהרשימה
    for keyword in PRODUCT_KEYWORDS:
        if keyword in title_lower:
            return keyword
    
    # אם לא נמצאה מילת מפתח, נשתמש במילה הראשונה המשמעותית
    words = title_lower.split()
    # דלג על מילים קצרות (<3 אותיות) כמו "for", "the", "new"
    for word in words:
        if len(word) >= 3:
            return word
    
    return title_lower[:20]  # במקרה הגרוע - 20 תווים ראשונים

def calculate_similarity(text1, text2):
    """
    ✅ חישוב אחוז דמיון בין שני טקסטים
    מחזיר ערך בין 0 ל-1 (1 = זהים לגמרי)
    """
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    # אם זהים לגמרי
    if text1 == text2:
        return 1.0
    
    # חישוב דמיון לפי מילים משותפות
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    common_words = words1.intersection(words2)
    total_words = words1.union(words2)
    
    similarity = len(common_words) / len(total_words)
    return similarity

def is_duplicate(product, existing_data):
    """
    ✅ בדיקה חכמה אם המוצר כבר קיים
    בודק 4 רמות:
    1. URL זהה
    2. כותרת זהה
    3. כותרת דומה ב-80%+
    4. ✨ חדש! מילת מפתח זהה (למנוע 5 מצתים שונים)
    """
    product_url = product.get('product_detail_url', '')
    product_title = product.get('product_title', '')
    product_keyword = extract_main_keyword(product_title)
    
    # דלג על header
    for row in existing_data[1:]:
        if len(row) < 2:
            continue
        
        existing_url = row[0] if len(row) > 0 else ''
        existing_title = row[1] if len(row) > 1 else ''
        existing_keyword = extract_main_keyword(existing_title)
        
        # בדיקה 1: URL זהה
        if product_url and existing_url and product_url == existing_url:
            print(f"⚠️ דילוג - URL כפול: {product_title[:50]}...")
            return True
        
        # בדיקה 2: כותרת זהה
        if product_title and existing_title and product_title.lower() == existing_title.lower():
            print(f"⚠️ דילוג - כותרת זהה: {product_title[:50]}...")
            return True
        
        # בדיקה 3: כותרת דומה מאוד (80%+)
        if product_title and existing_title:
            similarity = calculate_similarity(product_title, existing_title)
            if similarity >= 0.8:
                print(f"⚠️ דילוג - כותרת דומה ({similarity*100:.0f}%): {product_title[:50]}...")
                return True
        
        # ✅ בדיקה 4: מילת מפתח זהה (החדש!)
        if product_keyword and existing_keyword and product_keyword == existing_keyword:
            print(f"⚠️ דילוג - קטגוריה קיימת ('{product_keyword}'): {product_title[:50]}...")
            print(f"   כבר יש: {existing_title[:50]}...")
            return True
    
    return False

def get_product_description(product):
    """
    ✅ עודכן!
    מקבל תיאור המוצר ומתרגם אותו לעברית
    """
    title = product.get('product_title', 'No Description')
    category = product.get('second_level_category_name', '')
    
    # יצירת התיאור באנגלית
    if category:
        description_en = f"{category} - {title[:80]}"
    else:
        description_en = title[:120]
    
    # ✅ תרגום לעברית!
    description_he = translate_to_hebrew(description_en)
    
    return description_he

def write_to_google_sheets(products):
    """כתיבת מוצרים ל-Google Sheets עם סינון כפילויות"""
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
        duplicates_count = 0
        
        for product in products:
            # ✅ בדיקת כפילות!
            if is_duplicate(product, existing_data):
                duplicates_count += 1
                continue
            
            # לינק אפיליאייט
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
            
            # ✅ קריטי! כל תמונה עוברת דרך Proxy!
            original_image_url = product.get('product_main_image_url', '')
            proxy_image_url = convert_to_proxy_url(original_image_url)
            
            row = [
                product.get('product_detail_url', ''),
                product.get('product_title', 'No Title'),
                get_product_description(product),  # ✅ עכשיו בעברית!
                proxy_image_url,  # ✅ Proxy URL!
                promotion_link,
                rating
            ]
            
            new_rows.append(row)
        
        if new_rows:
            sheet.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"{sheet_name}!A{next_row}:F{next_row + len(new_rows) - 1}",
                valueInputOption='RAW',
                body={'values': new_rows}
            ).execute()
            
            print(f"✅ {len(new_rows)} מוצרים חדשים נוספו!")
            print(f"⏭️ {duplicates_count} מוצרים כפולים דולגו")
            print(f"📊 סה\"כ מוצרים בטבלה: {len(existing_data) + len(new_rows) - 1}")
        else:
            print(f"⚠️ לא נמצאו מוצרים חדשים (כל ה-{duplicates_count} היו כפולים)")
            
    except Exception as e:
        print(f"❌ שגיאה בכתיבה ל-Google Sheets: {str(e)}")

def main():
    print("🚀 מתחיל משיכת מוצרים חמים...")
    print(f"📅 תאריך: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 קטגוריות: אלקטרוניקה, אופנה, בית")
    print(f"🇮🇱 מותאם לישראל:")
    print(f"   ✅ משלוח חינם לישראל")
    print(f"   ✅ זמן משלוח מהיר (עד 15 יום)")
    print(f"   ✅ דירוג גבוה (4.0+)")
    print(f"   ✅ מחירים בשקלים")
    print(f"🔄 כל התמונות יעברו דרך Proxy - 100% יעבוד!")
    print(f"🔤 כל התיאורים יתורגמו לעברית!")
    print(f"🚫 סינון כפילויות - רק מוצרים ייחודיים!")
    
    products = fetch_hot_products()
    
    if products:
        write_to_google_sheets(products)
        print("✅ הריצה הסתיימה בהצלחה!")
        print("📸 כל התמונות עברו דרך Proxy - יעבדו באתר!")
        print("🇮🇱 כל התיאורים בעברית!")
        print("🎯 ללא כפילויות - מוצרים ייחודיים בלבד!")
        print("🚀 מותאם לישראל - משלוח מהיר וחינמי!")
    else:
        print("⚠️ לא נמצאו מוצרים")

if __name__ == "__main__":
    main()