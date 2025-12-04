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

def generate_signature(params, secret):
    sorted_params = sorted(params.items())
    sign_string = secret
    for key, value in sorted_params:
        sign_string += f"{key}{value}"
    sign_string += secret
    
    # Simple MD5 - exactly like the original code!
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()

def fetch_products():
    timestamp = str(int(time.time() * 1000))
    
    params = {
        'app_key': str(ALIEXPRESS_APP_KEY),
        'timestamp': str(timestamp),
        'sign_method': 'md5',
        'method': 'aliexpress.affiliate.hotproduct.query',
        'format': 'json',
        'v': '2.0',
        'page_size': '30',
        'page_no': '1',
        'sort': 'SALE_PRICE_ASC',
        'target_currency': 'USD',
        'target_language': 'EN',
        'tracking_id': str(ALIEXPRESS_TRACKING_ID),
    }
    
    params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
    url = "https://api-sg.aliexpress.com/sync"
    
    try:
        print(f"API Call...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"API Response: {json.dumps(data, indent=2)[:500]}...")
        
        if 'aliexpress_affiliate_hotproduct_query_response' in data:
            result = data['aliexpress_affiliate_hotproduct_query_response']['resp_result']
            result_data = json.loads(result['resp_code']) if isinstance(result['resp_code'], str) else result
            
            if result_data.get('resp_code') == 200:
                products = result_data.get('result', {}).get('products', {}).get('product', [])
                print(f"Found {len(products)} products!")
                return products
            else:
                print(f"Error: {result_data.get('resp_msg', 'Unknown error')}")
                return []
        else:
            print("Unexpected response format")
            return []
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

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

def is_duplicate(product_url, existing_products):
    for existing in existing_products:
        if existing['url'] in product_url or product_url in existing['url']:
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
    print(f"App Secret length: {len(ALIEXPRESS_APP_SECRET) if ALIEXPRESS_APP_SECRET else 0}\n")
    
    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("Missing API Keys!")
        return
    
    try:
        existing_products = get_existing_products()
        products = fetch_products()
        
        if not products:
            print("No products found")
            return
        
        all_new = []
        
        for product in products:
            try:
                url = product.get('product_detail_url', '')
                title = product.get('product_title', '')
                
                if not url or not title:
                    continue
                
                if is_duplicate(url, existing_products):
                    continue
                
                promotion_link = product.get('promotion_link', url)
                image = product.get('product_main_image_url', '')
                
                all_new.append({
                    'url': url,
                    'title': title,
                    'description': title[:120],
                    'image': image,
                    'affiliate_link': promotion_link
                })
                
                existing_products.append({'url': url, 'title': title})
                
                print(f"Added: {title[:50]}...")
                
                if len(all_new) >= 30:
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