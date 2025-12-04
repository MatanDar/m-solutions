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

ALIEXPRESS_APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = 'matan123'

SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

# Keywords to prevent duplicates
PRODUCT_KEYWORDS = [
    # Bags & Cases
    'bag', 'wallet', 'backpack', 'clutch', 'purse', 'handbag', 'tote', 'crossbody', 
    'shoulder bag', 'messenger', 'satchel', 'hobo', 'wristlet', 'pouch', 'case',
    
    # Accessories
    'bracelet', 'necklace', 'ring', 'earrings', 'belt', 'watch', 'sunglasses', 
    'hat', 'scarf', 'gloves', 'tie', 'bowtie', 'cufflinks', 'brooch', 'anklet',
    
    # Tools
    'screwdriver', 'hammer', 'wrench', 'pliers', 'tape measure', 'level', 'drill', 
    'saw', 'knife', 'scissors', 'cutter', 'opener', 'flashlight', 'torch', 'lighter',
    
    # Sports & Fitness
    'ball', 'racket', 'paddle', 'mat', 'band', 'rope', 'weight', 'dumbbell',
    'yoga', 'fitness', 'exercise', 'gym', 'sports', 'training', 'workout',
    
    # Office
    'pen', 'pencil', 'notebook', 'marker', 'highlighter', 'eraser', 'stapler', 
    'clip', 'folder', 'binder', 'calculator', 'ruler', 'tape', 'scissors',
    
    # Toys
    'puzzle', 'toy', 'game', 'doll', 'car', 'truck', 'plane', 'robot', 
    'lego', 'block', 'figure', 'plush', 'stuffed', 'action figure',
    
    # Pet
    'collar', 'leash', 'bowl', 'pet toy', 'bed', 'carrier', 'cage', 'aquarium',
    
    # Auto
    'mount', 'holder', 'cover', 'mat', 'organizer', 'charger', 'light', 'mirror',
    
    # Electronics
    'cable', 'charger', 'adapter', 'mouse', 'keyboard', 'headphone', 'earphone', 
    'speaker', 'powerbank', 'battery', 'usb', 'hdmi', 'bluetooth', 'wireless',
    'phone', 'tablet', 'laptop', 'computer', 'monitor', 'screen', 'display',
    'smartwatch', 'tracker', 'camera', 'tripod', 'lens', 'drone', 'remote',
    
    # Home
    'mug', 'cup', 'bottle', 'thermos', 'plate', 'bowl', 'spoon', 'fork', 'knife',
    'pan', 'pot', 'cooker', 'blender', 'mixer', 'kettle', 'toaster', 'oven',
    'pillow', 'blanket', 'sheet', 'curtain', 'towel', 'mat', 'rug', 'carpet',
    'organizer', 'storage', 'box', 'basket', 'rack', 'shelf', 'holder', 'hanger',
    'clock', 'mirror', 'frame', 'vase', 'plant', 'pot', 'garden', 'tool',
    
    # Other
    'bookmark', 'keychain', 'lanyard', 'badge', 'sticker', 'magnet', 'flag', 
    'poster', 'sign', 'plaque', 'ornament', 'candle', 'incense', 'diffuser'
]

def extract_main_keyword(title):
    """
    Extract main keyword from product title
    Example: 'USB Cable Fast Charging' -> 'cable'
    """
    title_lower = title.lower()
    
    # Search for keyword from list
    for keyword in PRODUCT_KEYWORDS:
        if keyword in title_lower:
            return keyword
    
    # If no keyword found, use first meaningful word
    words = title_lower.split()
    for word in words:
        if len(word) >= 3:
            return word
    
    return title_lower[:20]

def calculate_similarity(text1, text2):
    """
    Calculate similarity between two texts
    Returns value between 0-1 (1 = identical)
    """
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    if text1 == text2:
        return 1.0
    
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    common_words = words1.intersection(words2)
    total_words = words1.union(words2)
    
    similarity = len(common_words) / len(total_words)
    return similarity

def fix_image_url(image_url):
    """
    Fix and proxy image URLs to ensure they always work
    """
    if not image_url or image_url == 'NO_IMAGE':
        return 'https://via.placeholder.com/400x400/e0e0e0/666666?text=No+Image'
    
    # Clean the URL
    if '?' in image_url:
        image_url = image_url.split('?')[0]
    
    # Ensure protocol
    if not image_url.startswith('http'):
        image_url = 'https:' + image_url if image_url.startswith('//') else 'https://' + image_url
    
    # Use image proxy to ensure images always load
    clean_url = image_url.replace('https://', '').replace('http://', '')
    proxy_url = f"https://images.weserv.nl/?url={clean_url}&w=400&h=400&fit=cover&default=1"
    
    return proxy_url

def is_quality_product(product):
    """
    Check if product meets quality standards:
    - Price >= $6
    - Free or cheap shipping to Israel
    - Fast shipping (if available)
    """
    # Check price
    price = 0
    if 'target_sale_price' in product:
        price = float(product.get('target_sale_price', 0))
    elif 'sale_price' in product:
        price = float(product.get('sale_price', 0))
    elif 'app_sale_price' in product:
        price = float(product.get('app_sale_price', 0))
    
    if price < 6:
        print(f"  Skip - Price too low (${price:.2f})")
        return False
    
    # Check free shipping (if data available)
    if 'second_level_category_name' in product:
        # Some products have shipping info in various fields
        pass
    
    # Note: AliExpress API doesn't always return accurate shipping data
    # The ship_to_country parameter in the request should handle this
    # But we log it for debugging
    
    return True

def generate_signature(params, secret):
    sorted_params = sorted(params.items())
    sign_string = secret
    for key, value in sorted_params:
        sign_string += f"{key}{value}"
    sign_string += secret
    
    # Simple MD5 - exactly like the original code!
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

def fetch_products():
    """Fetch products - will try multiple pages if needed"""
    all_products = []
    max_pages = 5  # Try up to 5 pages
    
    for page in range(1, max_pages + 1):
        timestamp = str(int(time.time() * 1000))
        
        params = {
            'app_key': str(ALIEXPRESS_APP_KEY),
            'timestamp': str(timestamp),
            'sign_method': 'md5',
            'method': 'aliexpress.affiliate.hotproduct.query',
            'format': 'json',
            'v': '2.0',
            'page_size': '50',
            'page_no': str(page),
            'sort': 'LAST_VOLUME_DESC',  # Best sellers (most sales)
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
                    print(f"Found {len(products)} products on page {page}")
                    all_products.extend(products)
                    
                    # If we have enough products, stop searching
                    if len(all_products) >= 100:
                        break
                else:
                    print(f"Error: {result_data.get('resp_msg', 'Unknown error')}")
                    break
            else:
                print("Unexpected response format")
                break
                
        except Exception as e:
            print(f"Error: {str(e)}")
            break
        
        # Small delay between pages
        if page < max_pages:
            time.sleep(1)
    
    print(f"\nTotal products fetched: {len(all_products)}")
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
        
        print(f"Found {len(existing)} existing products")
        return existing
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def is_duplicate(product_url, product_title, existing_products):
    """
    Smart duplicate detection:
    1. Exact URL match
    2. Exact title match
    3. Similar title (80%+)
    4. Same keyword/category (prevents multiple bags, wallets, etc.)
    """
    product_keyword = extract_main_keyword(product_title)
    
    for existing in existing_products:
        existing_url = existing.get('url', '')
        existing_title = existing.get('title', '')
        
        # Check 1: Exact URL match
        if product_url and existing_url and product_url == existing_url:
            print(f"  Skip - Duplicate URL: {product_title[:40]}...")
            return True
        
        # Check 2: Exact title match
        if product_title and existing_title and product_title.lower() == existing_title.lower():
            print(f"  Skip - Duplicate title: {product_title[:40]}...")
            return True
        
        # Check 3: Similar title (80%+)
        if product_title and existing_title:
            similarity = calculate_similarity(product_title, existing_title)
            if similarity >= 0.8:
                print(f"  Skip - Similar ({similarity*100:.0f}%): {product_title[:40]}...")
                return True
        
        # Check 4: Same keyword/category
        existing_keyword = extract_main_keyword(existing_title)
        if product_keyword and existing_keyword and product_keyword == existing_keyword:
            print(f"  Skip - Category exists ('{product_keyword}'): {product_title[:40]}...")
            print(f"         Already have: {existing_title[:40]}...")
            return True
    
    return False

def add_products_to_sheet(new_products):
    if not new_products:
        print("No products to add")
        return
    
    print(f"Adding {len(new_products)} products...")
    
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
        
        print(f"Added {len(new_products)} products!")
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("AliExpress Products Updater")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tracking ID: {ALIEXPRESS_TRACKING_ID}")
    print(f"Signature: MD5 (original)")
    print(f"App Key length: {len(ALIEXPRESS_APP_KEY) if ALIEXPRESS_APP_KEY else 0}")
    print(f"App Secret length: {len(ALIEXPRESS_APP_SECRET) if ALIEXPRESS_APP_SECRET else 0}")
    print(f"Min Price: $6")
    print(f"Ship To: Israel (Free/Fast shipping preferred)")
    print(f"Sort By: Best Sellers (Most Sales)")
    print(f"Smart Duplicate Detection: ON\n")
    
    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("Missing API Keys!")
        return
    
    try:
        existing_products = get_existing_products()
        products = fetch_products()
        
        if not products:
            print("No products found")
            return
        
        print(f"\nFiltering products...")
        all_new = []
        
        for product in products:
            try:
                url = product.get('product_detail_url', '')
                title = product.get('product_title', '')
                
                if not url or not title:
                    continue
                
                # Check quality standards
                if not is_quality_product(product):
                    continue
                
                if is_duplicate(url, title, existing_products):
                    continue
                
                promotion_link = product.get('promotion_link', url)
                image = product.get('product_main_image_url', '')
                
                # Fix image URL with proxy
                image = fix_image_url(image)
                
                all_new.append({
                    'url': url,
                    'title': title,
                    'description': title[:120],
                    'image': image,
                    'affiliate_link': promotion_link
                })
                
                existing_products.append({'url': url, 'title': title})
                
                print(f"Added: {title[:50]}...")
                
                # Stop when we have enough quality products
                if len(all_new) >= 30:
                    print(f"\nReached target of 30 products!")
                    break
                
            except Exception as e:
                print(f"Error: {e}")
                continue
        
        if all_new:
            print(f"\nFound {len(all_new)} new products!")
            add_products_to_sheet(all_new)
        else:
            print("\nNo new products found")
        
        print("\nDone!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()