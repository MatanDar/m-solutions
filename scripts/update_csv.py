import os
import csv
import hashlib
import hmac
import time
import requests
import sys
import json
from datetime import datetime

# AliExpress API configuration
APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
TRACKING_ID = os.environ.get('ALIEXPRESS_TRACKING_ID', 'default')

# CSV file path
CSV_FILE = 'products.csv'

def generate_sign(params, secret):
    """Generate signature for AliExpress API request using HMAC-SHA256"""
    # Sort parameters by key
    sorted_params = sorted(params.items())
    
    # Create sign string (concatenate all params)
    sign_string = ""
    for key, value in sorted_params:
        if key not in ['sign']:  # Don't include sign itself
            sign_string += f"{key}{value}"
    
    # Generate HMAC-SHA256 hash
    return hmac.new(
        secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()

def fetch_hot_products(page_size=20):
    """Fetch hot/bestselling products from AliExpress"""
    
    if not APP_KEY or not APP_SECRET:
        print("❌ Error: API credentials not found!")
        print("Please set ALIEXPRESS_APP_KEY and ALIEXPRESS_APP_SECRET in GitHub Secrets")
        return []
    
    # API endpoint
    api_url = "https://api-sg.aliexpress.com/sync"
    
    # API method
    api_name = "aliexpress.affiliate.hotproduct.query"
    
    # Request parameters
    timestamp = str(int(time.time() * 1000))
    params = {
        'app_key': APP_KEY,
        'method': api_name,
        'timestamp': timestamp,
        'format': 'json',
        'v': '2.0',
        'sign_method': 'sha256',
        'target_currency': 'USD',
        'target_language': 'EN',
        'tracking_id': TRACKING_ID,
        'page_size': str(page_size)
    }
    
    # Generate signature
    sign = generate_sign(params, APP_SECRET)
    params['sign'] = sign
    
    try:
        print(f"🔍 Fetching hot products from AliExpress...")
        print(f"📡 Using App Key: {APP_KEY[:8]}...")
        
        response = requests.get(api_url, params=params, timeout=30)
        
        # Debug output
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return []
        
        data = response.json()
        
        # Check for errors
        if 'error_response' in data:
            error = data['error_response']
            error_code = error.get('code', 'unknown')
            error_msg = error.get('msg', 'Unknown error')
            print(f"❌ API Error [{error_code}]: {error_msg}")
            print(f"📄 Full response: {json.dumps(data, indent=2)[:500]}")
            return []
        
        # Extract products
        if 'aliexpress_affiliate_hotproduct_query_response' in data:
            resp_result = data['aliexpress_affiliate_hotproduct_query_response'].get('resp_result')
            
            if resp_result:
                result = resp_result.get('result', {})
                products = result.get('products', {}).get('product', [])
                
                if products:
                    print(f"✅ Found {len(products)} hot products!")
                    return products
                else:
                    print("⚠️  No products returned in response")
                    return []
            else:
                print("⚠️  No resp_result in response")
                return []
        else:
            print("❌ Unexpected API response format")
            print(f"📄 Response keys: {list(data.keys())}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        print(f"Response text: {response.text[:200]}")
        return []
    except Exception as e:
        print(f"❌ Error fetching products: {e}")
        import traceback
        traceback.print_exc()
        return []

def read_existing_products():
    """Read existing products from CSV to avoid duplicates"""
    existing_urls = set()
    
    if not os.path.exists(CSV_FILE):
        print(f"ℹ️  CSV file not found, will create new one")
        return existing_urls
    
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('PRODUCT_URL'):
                    existing_urls.add(row['PRODUCT_URL'].strip())
        
        print(f"📊 Found {len(existing_urls)} existing products in CSV")
        return existing_urls
        
    except Exception as e:
        print(f"⚠️  Error reading CSV: {e}")
        return existing_urls

def update_csv(products):
    """Add new products to CSV file"""
    
    if not products:
        print("ℹ️  No products to add")
        return
    
    # Read existing products
    existing_urls = read_existing_products()
    
    # Prepare new products
    new_products = []
    for product in products:
        product_url = product.get('product_detail_url', '')
        
        # Skip if already exists
        if product_url in existing_urls:
            continue
        
        # Extract product data
        title = product.get('product_title', 'No title')
        image_url = product.get('product_main_image_url', '')
        affiliate_link = product.get('promotion_link', product_url)
        
        # Create description from available data
        sale_price = product.get('target_sale_price', '')
        original_price = product.get('target_original_price', '')
        discount = product.get('discount', '')
        
        description_parts = []
        if sale_price:
            description_parts.append(f"Sale Price: ${sale_price}")
        if original_price and original_price != sale_price:
            description_parts.append(f"Original: ${original_price}")
        if discount:
            description_parts.append(f"Discount: {discount}")
        
        description = " | ".join(description_parts) if description_parts else "Hot product from AliExpress"
        
        new_products.append({
            'PRODUCT_URL': product_url,
            'TITLE': title,
            'DESCRIPTION': description,
            'IMAGE_URL': image_url,
            'AFFILIATE_LINK': affiliate_link
        })
    
    if not new_products:
        print("✅ No new products to add (all already exist in CSV)")
        return
    
    # Write to CSV
    try:
        file_exists = os.path.exists(CSV_FILE)
        
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['PRODUCT_URL', 'TITLE', 'DESCRIPTION', 'IMAGE_URL', 'AFFILIATE_LINK']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header if file is new
            if not file_exists:
                writer.writeheader()
            
            # Write new products
            writer.writerows(new_products)
        
        print(f"✅ Successfully added {len(new_products)} new products to {CSV_FILE}")
        
        # Print summary
        print("\n📋 New products added:")
        for i, product in enumerate(new_products[:5], 1):  # Show first 5
            print(f"   {i}. {product['TITLE'][:60]}...")
        
        if len(new_products) > 5:
            print(f"   ... and {len(new_products) - 5} more")
            
    except Exception as e:
        print(f"❌ Error writing to CSV: {e}")
        sys.exit(1)

def main():
    """Main function"""
    print("=" * 60)
    print("🔥 AliExpress Hot Products Updater")
    print("=" * 60)
    print(f"📅 Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch products
    products = fetch_hot_products(page_size=20)
    
    if not products:
        print("\n⚠️  No products fetched. Please check your API credentials.")
        print("\n🔍 Troubleshooting:")
        print("   1. Verify your App Key and App Secret in GitHub Secrets")
        print("   2. Make sure your app is 'Online' in AliExpress Open Platform")
        print("   3. Check if your app has 'Affiliate API' permissions")
        sys.exit(1)
    
    # Update CSV
    update_csv(products)
    
    print("\n" + "=" * 60)
    print("✅ Update completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()