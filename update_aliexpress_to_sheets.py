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

try:
    from googletrans import Translator
    translator = Translator()
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("⚠️ googletrans not available, using English only")

# ============ CATEGORY MAPPING ============
# מיפוי חכם של מילות מפתח לקטגוריות
CATEGORY_MAPPING = {
    'מוצרי חשמל': [
        'consumer electronics', 'lights', 'lighting', 'electrical', 'led', 'lamp', 
        'bulb', 'power', 'battery', 'appliances', 'gadget', 'device'
    ],
    'מטבח ובית': [
        'home', 'kitchen', 'dining', 'tableware', 'cookware', 'appliances',
        'furniture', 'bedding', 'bath', 'storage', 'organization', 'decor',
        'garden', 'cleaning', 'laundry', 'towel', 'curtain', 'pillow', 'blanket'
    ],
    'ספורט וכושר': [
        'sports', 'fitness', 'gym', 'exercise', 'yoga', 'running', 'cycling',
        'outdoor', 'camping', 'hiking', 'swimming', 'workout', 'training',
        'athletic', 'ball', 'racket', 'dumbbell', 'weight'
    ],
    'תיקים ואביזרים': [
        'bags', 'bag', 'luggage', 'backpack', 'wallet', 'handbag', 'purse', 
        'case', 'pouch', 'travel', 'accessories', 'jewelry', 'watches', 'watch',
        'sunglasses', 'glasses', 'belt', 'scarf', 'hat', 'gloves', 'bracelet',
        'necklace', 'earrings', 'ring'
    ],
    'כלי עבודה': [
        'tools', 'tool', 'hardware', 'construction', 'drill', 'saw', 'hammer',
        'wrench', 'screwdriver', 'measuring', 'safety', 'industrial',
        'automotive', 'repair', 'maintenance', 'flashlight', 'knife'
    ],
    'צעצועים': [
        'toys', 'toy', 'games', 'game', 'hobbies', 'kids', 'children', 'baby', 
        'puzzle', 'doll', 'action figure', 'model', 'educational', 'remote control',
        'stuffed', 'plush', 'lego', 'block'
    ],
    'אופנה': [
        'clothing', 'fashion', 'apparel', 'shoes', 'shoe', 'men', 'women', 'dress',
        'shirt', 'pants', 'jacket', 'coat', 'sweater', 'underwear', 'socks',
        'boots', 'sneakers', 'sandals', 't-shirt', 'jeans'
    ],
    'מוצרים לטלפון': [
        'phone', 'mobile', 'smartphone', 'charger', 'cable', 'adapter', 
        'headphone', 'earphone', 'earbuds', 'speaker', 'bluetooth', 'wireless',
        'usb', 'screen protector', 'phone case', 'selfie stick', 'power bank',
        'holder', 'stand', 'mount', 'tablet', 'iphone', 'android', 'samsung'
    ]
}

def map_to_category(title, description, aliexpress_category):
    """
    מיפוי חכם לקטגוריה לפי:
    1. מילות מפתח בכותרת
    2. מילות מפתח בתיאור
    3. קטגוריית AliExpress
    """
    text_to_search = f"{title} {description} {aliexpress_category}".lower()
    
    category_scores = {}
    
    for category, keywords in CATEGORY_MAPPING.items():
        score = 0
        for keyword in keywords:
            if keyword in text_to_search:
                if keyword in title.lower():
                    score += 3
                else:
                    score += 1
        
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        return best_category
    
    # ברירת מחדל - מוצרים לטלפון
    return 'מוצרים לטלפון'

# ============ REST OF THE CODE ============

ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = 'matan123'

SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

PRODUCT_KEYWORDS = [
    'bag', 'wallet', 'backpack', 'clutch', 'purse', 'handbag', 'tote', 'crossbody', 
    'shoulder bag', 'messenger', 'satchel', 'hobo', 'wristlet', 'pouch', 'case',
    'bracelet', 'necklace', 'ring', 'earrings', 'belt', 'watch', 'sunglasses', 
    'hat', 'scarf', 'gloves', 'tie', 'bowtie', 'cufflinks', 'brooch', 'anklet',
    'screwdriver', 'hammer', 'wrench', 'pliers', 'tape measure', 'level', 'drill', 
    'saw', 'knife', 'scissors', 'cutter', 'opener', 'flashlight', 'torch', 'lighter',
    'ball', 'racket', 'paddle', 'mat', 'band', 'rope', 'weight', 'dumbbell',
    'yoga', 'fitness', 'exercise', 'gym', 'sports', 'training', 'workout',
    'pen', 'pencil', 'notebook', 'marker', 'highlighter', 'eraser', 'stapler', 
    'clip', 'folder', 'binder', 'calculator', 'ruler', 'tape', 'scissors',
    'puzzle', 'toy', 'game', 'doll', 'car', 'truck', 'plane', 'robot', 
    'lego', 'block', 'figure', 'plush', 'stuffed', 'action figure',
    'collar', 'leash', 'bowl', 'bed', 'treat', 'shampoo', 'brush',
    'grooming', 'cage', 'carrier', 'aquarium', 'fish', 'bird', 'hamster'
]

def translate_to_hebrew(text):
    """Translate text to Hebrew"""
    if not TRANSLATOR_AVAILABLE:
        return text
    
    try:
        if not text or len(text.strip()) == 0:
            return text
        
        text = text[:500]
        translated = translator.translate(text, src='en', dest='he')
        return translated.text
    except Exception as e:
        print(f"  Translation error: {e}")
        return text

def create_description(product):
    """Create Hebrew description"""
    title = product.get('product_title', 'No Description')
    category = product.get('second_level_category_name', '')
    
    if category:
        description_en = f"{category} - {title[:80]}"
    else:
        description_en = title[:120]
    
    description_he = translate_to_hebrew(description_en)
    return description_he

def fix_image_url(image_url):
    """Fix image URL"""
    if not image_url:
        return ''
    return image_url

def is_quality_product(product):
    """Check quality standards"""
    try:
        sale_price_str = product.get('target_sale_price', '0')
        try:
            sale_price = float(sale_price_str)
        except (ValueError, TypeError):
            return False
        
        if sale_price < 6.0:
            return False
        
        return True
    except Exception as e:
        return False

def is_duplicate(url, title, existing_products):
    """Smart duplicate detection"""
    title_lower = title.lower()
    
    for existing in existing_products:
        existing_url = existing.get('url', '')
        existing_title = existing.get('title', '').lower()
        
        if url == existing_url:
            print(f"  Skip - Same URL: {title[:40]}...")
            return True
        
        if len(title_lower) > 10:
            words_new = set(title_lower.split())
            words_existing = set(existing_title.split())
            if words_new and words_existing:
                similarity = len(words_new & words_existing) / len(words_new | words_existing)
                if similarity > 0.9:
                    print(f"  Skip - Similar title ({similarity:.0%}): {title[:40]}...")
                    return True
        
        if title_lower == existing_title:
            print(f"  Skip - Exact title: {title[:40]}...")
            return True
    
    return False

def generate_signature(params, secret):
    sorted_params = sorted(params.items())
    sign_string = secret
    for key, value in sorted_params:
        sign_string += f"{key}{value}"
    sign_string += secret
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

def fetch_products(max_pages=30):
    print(f"Fetching products from AliExpress API...")
    print(f"📄 Scanning up to 30 pages (1500 products max) - Ship to Israel only 🇮🇱")
    all_products = []
    page = 1
    
    while page <= max_pages:
        params = {
            'app_key': str(ALIEXPRESS_APP_KEY),
            'timestamp': str(int(time.time() * 1000)),
            'method': 'aliexpress.affiliate.hotproduct.query',
            'sign_method': 'md5',
            'format': 'json',
            'v': '2.0',
            'page_size': '50',
            'page_no': str(page),
            'sort': 'LAST_VOLUME_DESC',
            'target_currency': 'USD',
            'target_language': 'EN',
            'tracking_id': str(ALIEXPRESS_TRACKING_ID),
            'ship_to_country': 'IL',
        }
        
        params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
        url = "https://api-sg.aliexpress.com/sync"
        
        try:
            print(f"API Call (Page {page})...")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'aliexpress_affiliate_hotproduct_query_response' in data:
                result = data['aliexpress_affiliate_hotproduct_query_response']['resp_result']
                result_data = json.loads(result['resp_code']) if isinstance(result['resp_code'], str) else result
                
                if result_data.get('resp_code') == 200:
                    products = result_data.get('result', {}).get('products', {}).get('product', [])
                    print(f"  Found {len(products)} products")
                    all_products.extend(products)
                    
                    if len(all_products) >= 1500:
                        print(f"  Collected enough products ({len(all_products)}), stopping")
                        break
                else:
                    print(f"  Error: {result_data.get('resp_msg', 'Unknown error')}")
                    break
            else:
                print("  Unexpected response format")
                break
                
        except Exception as e:
            print(f"  Error: {str(e)}")
            break
        
        page += 1
        if page <= max_pages:
            time.sleep(2)  # Prevent rate limit
    
    print(f"\nTotal products fetched: {len(all_products)}\n")
    return all_products

def get_existing_products():
    print("Loading existing products...")
    
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
            range=f'{SHEET_NAME}!A:G'
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            return []
        
        products = []
        for row in values[1:]:
            if len(row) >= 2:
                products.append({
                    'url': row[0] if len(row) > 0 else '',
                    'title': row[1] if len(row) > 1 else ''
                })
        
        print(f"Found {len(products)} existing products\n")
        return products
        
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

def add_products_to_sheet(products):
    print(f"\nAdding {len(products)} products to sheet...")
    
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        rows = [[
            p.get('url', ''),
            p.get('title', ''),
            p.get('description', ''),
            p.get('image', ''),
            p.get('affiliate_link', ''),
            p.get('last_updated', ''),
            p.get('category', 'מוצרים לטלפון')
        ] for p in products]
        
        body = {'values': rows}
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:G',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✅ Added {result.get('updates', {}).get('updatedRows', 0)} rows")
        
    except Exception as e:
        print(f"Error adding products: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🔥 AliExpress Auto-Update - 4x Daily 🔥")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tracking ID: {ALIEXPRESS_TRACKING_ID}")
    print(f"\n📊 Settings:")
    print(f"  • Min Price: $6")
    print(f"  • Categories: 8 (no 'כללי')")
    print(f"  • Default: מוצרים לטלפון")
    print(f"  • Target: 5+ products per run")
    print(f"  • Pages to scan: 30 (1500 products max)")
    print(f"  • Ship to: Israel only 🇮🇱")
    print("=" * 60 + "\n")
    
    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("❌ Missing API Keys!")
        return
    
    try:
        existing_products = get_existing_products()
        products = fetch_products()
        
        if not products:
            print("⚠️ No products found")
            return
        
        print(f"\nFiltering products...")
        all_new = []
        products_checked = 0
        
        for product in products:
            try:
                products_checked += 1
                
                url = product.get('product_detail_url', '')
                title = product.get('product_title', '')
                
                if not url or not title:
                    continue
                
                if not is_quality_product(product):
                    continue
                
                if is_duplicate(url, title, existing_products):
                    continue
                
                promotion_link = product.get('promotion_link', url)
                image = product.get('product_main_image_url', '')
                image = fix_image_url(image)
                
                description = create_description(product)
                last_updated = datetime.now().strftime('%Y-%m-%d %H:%M')
                
                aliexpress_category = product.get('second_level_category_name', '')
                category = map_to_category(title, description, aliexpress_category)
                
                all_new.append({
                    'url': url,
                    'title': title,
                    'description': description,
                    'image': image,
                    'affiliate_link': promotion_link,
                    'last_updated': last_updated,
                    'category': category
                })
                
                existing_products.append({'url': url, 'title': title})
                
                print(f"✅ Added ({len(all_new)}): {title[:40]}... → {category}")
                
                if len(all_new) >= 5:
                    print(f"\n🎉 Success! Found {len(all_new)} quality products!")
                    break
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        if all_new:
            print(f"\n✅ Found {len(all_new)} new products!")
            add_products_to_sheet(all_new)
        else:
            print("\n⚠️ No new quality products found")
        
        print("\n✅ Done!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()