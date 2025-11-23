import os
import csv
import hashlib
import time
import requests
import sys
import json
from datetime import datetime
from urllib.parse import urlencode

# AliExpress API configuration
APP_KEY = os.environ.get('ALIEXPRESS_APP_KEY')
APP_SECRET = os.environ.get('ALIEXPRESS_APP_SECRET')
TRACKING_ID = os.environ.get('ALIEXPRESS_TRACKING_ID', 'matan')

# CSV file path
CSV_FILE = 'products.csv'

def generate_sign(api_path, params, secret):
    """Generate signature for AliExpress REST API"""
    # Sort parameters by key
    sorted_params = sorted(params.items())
    
    # Build sign string: api_path + key1value1key2value2...
    sign_string = api_path
    for key, value in sorted_params:
        if key != 'sign':
            sign_string += str(key) + str(value)
    
    # Generate HMAC-SHA256 hash
    import hmac
    return hmac.new(
        secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()

def fetch_hot_products(page_size=20):
    """Fetch hot/bestselling products from AliExpress using REST API"""
    
    if not APP_KEY or not APP_SECRET:
        print("❌ Error: API credentials not found!")
        print("Please set ALIEXPRESS_APP_KEY and ALIEXPRESS_APP_SECRET in GitHub Secrets")
        return []
    
    # REST API endpoint for hot products
    api_path = "/aliexpress/affiliate/hotproduct/query"
    api_url = f"https://api-sg.aliexpress.com/rest{api_path}"
    
    # Request parameters
    timestamp = str(int(time.time() * 1000))
    params = {
        'app_key': APP_KEY,
        'timestamp': timestamp,
        'sign_method': 'sha256',
        'target_currency': 'USD',
        'target_language': 'EN',
        'tracking_id': TRACKING_ID,
        'page_size': str(page_size)
    }
    
    # Generate signature with api_path
    sign = generate_sign(api_path, params, APP_SECRET)
    params['sign'] = sign
    
    try:
        print(f"🔍 Fetching hot products from AliExpress...")
        print(f"📡 Using REST API endpoint: {api_url}")
        print(f"📡 App Key: {APP_KEY[:3]}***")
        print(f"🔐 Sign method: sha256")
        
        # Make GET request with all params in URL
        response = requests.get(api_url, params=params, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
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
        
        # Extract products from response
        if 'aliexpress_affiliate_hotproduct_query_response' in data:
            resp_result = data['aliexpress_affiliate_hotproduct_query_response'].get('resp_result')
            
            if resp_result:
                result_data = resp_result.get('result', {})
                products = result_data.get('products', {}).get('product', [])
                
                if products:
                    print(f"✅ Found {len(products)} hot products!")
                    return products
                else:
                    print("⚠️  No products in response")
                    print(f"📄 Response structure: {json.dumps(data, indent=2)[:800]}")
                    return []
            else:
                print("⚠️  No resp_result in response")
                return []
        else:
            print("ℹ️  Different response format, checking alternatives...")
            # Sometimes the response format is different
            print(f"📄 Response keys: {list(data.keys())}")
            print(f"📄 Full response: {json.dumps(data, indent=2)[:800]}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        print(f"Response text: {response.text[:500]}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
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
    print("🔥 AliExpress Hot Products Updater v3 (REST API)")
    print("=" * 60)
    print(f"📅 Running at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch products
    products = fetch_hot_products(page_size=20)
    
    if not products:
        print("\n⚠️  No products fetched.")
        print("\n🔍 Troubleshooting:")
        print("   1. Verify API credentials in GitHub Secrets")
        print("   2. Make sure app is 'Online' in AliExpress Open Platform")
        print("   3. Check if app has 'Affiliate API' permissions")
        print("   4. Verify Tracking ID is correct")
        sys.exit(1)
    
    # Update CSV
    update_csv(products)
    
    print("\n" + "=" * 60)
    print("✅ Update completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()