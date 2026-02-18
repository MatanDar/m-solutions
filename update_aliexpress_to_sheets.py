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

# ============ CATEGORY MAPPING - Title-First Smart System ============
# מיפוי חכם: הכותרת מקבלת משקל גבוה, phrases מרובות מילים = יותר מדויק
# ברירת מחדל: מוצרי חשמל (לא מוצרים לטלפון - מדויק יותר)

CATEGORY_MAPPING = {
    'מוצרים לטלפון': [
        # מגנים ומסכים - ספציפי מאוד
        'phone case', 'iphone case', 'samsung case', 'phone cover', 'phone skin', 'back cover',
        'screen protector', 'tempered glass', 'glass protector', 'privacy glass',
        # סלפי ואחיזה
        'selfie stick', 'selfie ring', 'phone grip', 'phone ring holder', 'finger ring holder',
        # עמדות ומחזיקים לטלפון
        'phone holder', 'phone mount', 'car mount', 'car phone mount', 'phone stand',
        'phone dock', 'phone wallet case', 'phone strap', 'phone pouch',
        # טעינה ספציפית לטלפון
        'power bank', 'wireless charger', 'magsafe', 'magnetic charger', 'charging pad',
        # אוזניות
        'earbuds', 'airpods', 'tws', 'true wireless', 'in-ear headphone',
        # כבלים ספציפיים לטלפון
        'lightning cable', 'lightning charger', 'for iphone', 'for ipad',
        'for samsung galaxy', 'for android phone', 'for xiaomi', 'for huawei',
        # עדשות לטלפון
        'phone lens', 'phone camera lens', 'clip on lens',
        # מותגים ספציפיים = טלפון
        'iphone', 'ipad', 'airpods',
        # מפורשות טלפון
        'mobile phone', 'smartphone', 'android phone', 'cell phone'
    ],
    'מוצרי חשמל': [
        # בית חכם
        'smart home', 'smart plug', 'smart switch', 'smart bulb', 'smart light',
        'smart lamp', 'smart socket', 'wifi smart', 'smart doorbell',
        # מצלמות אבטחה
        'security camera', 'ip camera', 'wifi camera', 'cctv', 'nvr system', 'dvr system',
        'outdoor security', 'indoor security', 'baby monitor',
        # שואבי אבק חשמליים
        'robot vacuum', 'vacuum cleaner', 'robotic vacuum', 'cordless vacuum',
        # מזגנים ומאווררים
        'air conditioner', 'portable ac', 'air cooler', 'cooling fan',
        'electric fan', 'tower fan', 'ceiling fan', 'bladeless fan',
        # מטהרי אוויר ולחות
        'air purifier', 'humidifier', 'dehumidifier', 'air diffuser', 'essential oil diffuser',
        # תאורה
        'led strip', 'led light strip', 'strip light', 'neon light', 'rgb light',
        'desk lamp', 'floor lamp', 'table lamp', 'bedside lamp', 'led bulb', 'smart bulb',
        'led grow light', 'grow light',
        # מקרנים
        'projector', 'mini projector', 'portable projector', 'home projector',
        # מצלמות
        'dash cam', 'dashcam', 'action camera', 'body camera', 'car recorder',
        # רמקולים (לא אוזניות)
        'bluetooth speaker', 'portable speaker', 'soundbar', 'sound bar',
        'wireless speaker', 'outdoor speaker', 'desktop speaker',
        # שעוני חכם ופיטנס
        'smart watch', 'smartwatch', 'fitness band', 'fitness tracker', 'smart band',
        'gps watch', 'sport watch',
        # מוצרי טיפוח חשמליים
        'electric kettle', 'electric razor', 'electric shaver', 'electric toothbrush',
        'hair dryer', 'hair straightener', 'curling iron', 'hair curler', 'epilator',
        'face massager', 'skin care device',
        # ציוד חשמלי כללי
        'usb hub', 'usb splitter', 'power strip', 'extension cord', 'surge protector',
        'voltage tester', 'multimeter', 'clamp meter', 'soldering iron', 'heat gun', 'hot glue gun',
        'battery charger', 'solar panel', 'solar charger', 'power inverter',
        # רחפנים
        'drone', 'quadcopter', 'fpv drone', 'rc drone', 'aerial drone',
        # טלוויזיה ומולטימדיה
        'smart tv', 'tv box', 'android tv box', 'media player', 'hdmi switch',
        # תחבורה חשמלית
        'electric scooter', 'e-scooter', 'electric bicycle', 'e-bike', 'electric skateboard',
        'hover board'
    ],
    'מטבח ובית': [
        # בישול ואפייה
        'kitchen', 'cooking', 'baking', 'frying pan', 'sauce pan', 'wok pan', 'pot set',
        'knife set', 'cutting board', 'chopping board', 'peeler', 'grater', 'colander',
        'spatula', 'ladle', 'silicone tongs', 'whisk', 'rolling pin', 'pizza cutter',
        # אחסון מזון
        'food container', 'lunch box', 'food storage', 'mason jar', 'vacuum seal',
        'meal prep container', 'bento box', 'airtight container',
        # מוצרי קפה ותה
        'coffee maker', 'coffee grinder', 'french press', 'tea infuser', 'pour over',
        'blender', 'juicer', 'toaster oven', 'waffle maker', 'sandwich maker', 'egg cooker',
        'rice cooker', 'slow cooker', 'instant pot', 'pressure cooker',
        # ארגון מטבח
        'dish rack', 'dish drying rack', 'kitchen organizer', 'spice rack', 'spice jar',
        'drawer organizer', 'cabinet organizer', 'pot rack',
        # אמבטיה ושירותים
        'toilet brush', 'shower curtain', 'soap dispenser', 'bath mat set',
        'bathroom organizer', 'toilet paper holder', 'shower caddy',
        # כביסה וניקיון
        'laundry bag', 'clothes hanger', 'drying rack', 'ironing board', 'lint roller',
        'mop set', 'broom dustpan', 'cleaning brush', 'scrub sponge', 'microfiber towel',
        # מיטה ושינה
        'bed sheet set', 'pillow case', 'throw blanket', 'quilt cover', 'duvet cover', 'mattress topper',
        # עיצוב הבית
        'shower curtain', 'tablecloth', 'placemats', 'coaster set', 'candle holder',
        'picture frame', 'wall sticker', 'wall art print', 'wall clock', 'planter pot',
        'doormat', 'bath mat', 'area rug', 'chair cushion', 'sofa cover', 'throw pillow',
        # כלים לחדר אוכל
        'dinnerware set', 'plate set', 'bowl set', 'ceramic mug', 'wine glass', 'cutlery set'
    ],
    'ספורט וכושר': [
        # ציוד כושר
        'yoga mat', 'resistance band', 'pull up bar', 'push up board', 'ab roller wheel',
        'jump rope', 'skipping rope', 'dumbbell set', 'kettlebell', 'barbell', 'weight plate',
        'gym gloves', 'weightlifting belt', 'knee sleeve', 'knee brace',
        'wrist wrap', 'ankle support', 'elbow brace', 'compression sleeve',
        # ביגוד ספורט
        'running shoes', 'trail running', 'hiking boots', 'cycling shoes', 'tennis shoes',
        'sports bra', 'gym shorts', 'compression leggings', 'athletic wear',
        'running jacket', 'wind breaker running', 'track suit',
        # כדורים ומחבטים
        'soccer ball', 'basketball', 'volleyball', 'tennis racket', 'badminton racket',
        'table tennis paddle', 'ping pong', 'golf club', 'golf ball',
        # שחייה
        'swimming goggles', 'swim cap', 'wetsuit', 'diving mask', 'snorkel set',
        # קמפינג וטיולים
        'camping tent', 'sleeping bag', 'hiking backpack', 'trekking pole', 'camping stove',
        'camping lantern', 'survival kit', 'carabiner', 'hammock',
        # אופניים
        'bike helmet', 'cycling gloves', 'cycling jersey', 'bike light', 'bike lock',
        # אגרוף ואומנויות לחימה
        'boxing gloves', 'punching bag', 'mma gloves', 'kick boxing',
        # יוגה ופילאטיס
        'yoga block', 'yoga strap', 'foam roller', 'pilates ring', 'stretching band'
    ],
    'תיקים ואביזרים': [
        # תרמילים ותיקים
        'backpack', 'school bag', 'laptop backpack', 'shoulder bag', 'crossbody bag',
        'messenger bag', 'sling bag', 'fanny pack', 'waist bag', 'belt bag',
        'tote bag', 'handbag', 'clutch purse', 'evening bag', 'work tote',
        'travel bag', 'duffel bag', 'gym bag', 'weekender bag', 'diaper bag', 'camera bag',
        # ארנקים
        'wallet', 'card holder', 'money clip', 'coin purse', 'passport wallet',
        'rfid wallet', 'slim wallet', 'leather wallet', 'bifold wallet',
        # מזוודות
        'luggage set', 'suitcase', 'carry on bag', 'travel organizer', 'packing cube',
        # תכשיטים
        'necklace', 'pendant necklace', 'bracelet', 'earrings', 'stud earrings',
        'anklet', 'charm bracelet', 'statement necklace', 'ring jewelry',
        # משקפיים
        'sunglasses', 'reading glasses', 'blue light glasses', 'eyeglass frame',
        # כובעים
        'baseball cap', 'trucker hat', 'beanie hat', 'bucket hat', 'sun hat', 'snapback',
        # אביזרי שיער
        'hair band', 'scrunchie', 'hair clip', 'hair accessory', 'headband',
        # חגורות ורצועות שעון
        'leather belt', 'watch band', 'watch strap', 'apple watch band', 'smartwatch band'
    ],
    'כלי עבודה': [
        # כלי יד
        'screwdriver set', 'wrench set', 'combination pliers', 'claw hammer', 'hand saw',
        'hex key set', 'allen wrench', 'socket wrench', 'torque wrench', 'adjustable spanner',
        # מדידה
        'measuring tape', 'laser level', 'spirit level', 'laser distance', 'digital caliper',
        'angle finder', 'protractor',
        # כלי חיתוך
        'utility knife', 'box cutter', 'wire stripper', 'crimping tool', 'cable cutter', 'pipe cutter',
        # כלים חשמליים
        'electric drill', 'cordless drill', 'drill bit set', 'impact driver', 'rotary tool',
        'jigsaw', 'circular saw', 'angle grinder', 'belt sander', 'orbital sander',
        # ארגון כלים
        'tool set', 'hand tool kit', 'tool box', 'tool bag', 'tool organizer',
        # פנסים ותאורת עבודה
        'flashlight', 'headlamp', 'work light', 'tactical flashlight', 'torch',
        # סולמות
        'step ladder', 'extension ladder', 'folding ladder', 'telescoping ladder',
        # בטיחות
        'safety glasses', 'work gloves', 'ear muffs', 'dust mask', 'n95 mask', 'face shield',
        # רכב
        'car jack', 'floor jack', 'jump starter', 'tire inflator', 'oil filter wrench',
        'automotive tool', 'car repair', 'obd scanner',
        # חומרים
        'cable tie', 'zip tie', 'hose clamp', 'sandpaper', 'grinding wheel', 'cutting wheel'
    ],
    'צעצועים': [
        # לגו ובלוקים
        'lego set', 'building blocks', 'wooden blocks', 'magnetic tiles', 'construction set',
        # פאזלים
        'jigsaw puzzle', '3d puzzle', 'wooden puzzle', 'floor puzzle',
        # מכוניות שלט
        'remote control car', 'rc car', 'rc truck', 'rc robot', 'rc helicopter', 'rc boat',
        # רכבים לילדים
        'toy car set', 'toy truck', 'toy train set', 'diecast model', 'die cast car',
        # פיגרות ומודלים
        'action figure', 'anime figure', 'model kit', 'gundam',
        # בובות
        'doll house', 'baby doll', 'plush toy', 'stuffed animal', 'teddy bear', 'plush unicorn',
        # פידג׳ט
        'fidget spinner', 'pop it', 'stress relief toy', 'sensory toy', 'kinetic sand',
        # יצירה
        'slime kit', 'play doh set', 'diy craft kit', 'paint set for kids',
        # משחקי קופסה
        'board game', 'card game', 'chess set', 'monopoly style', 'tabletop game',
        # משחקי חוץ
        'kite flying', 'water gun toy', 'bubble machine', 'lawn game',
        # צעצועים חינוכיים
        'educational toy', 'montessori toy', 'stem kit', 'science kit',
        # אופניים וקורקינטים לילדים
        'kids bicycle', 'balance bike', 'kids kick scooter', 'ride on toy', 'push car'
    ],
    'אופנה': [
        # חולצות
        't-shirt', 'graphic tee', 'polo shirt', 'dress shirt', 'blouse', 'crop top', 'tank top',
        # מכנסיים
        'jeans', 'denim pants', 'chino pants', 'cargo trousers', 'jogger pants', 'wide leg pants',
        # שמלות וחצאיות
        'midi dress', 'maxi dress', 'mini dress', 'floral dress', 'bodycon dress',
        'a-line skirt', 'mini skirt', 'pleated skirt',
        # ג׳קטים ומעילים
        'denim jacket', 'leather jacket', 'varsity jacket', 'bomber jacket',
        'hoodie sweatshirt', 'zip up hoodie', 'cardigan sweater', 'knit sweater',
        'down puffer jacket', 'winter parka', 'trench coat', 'overcoat', 'windbreaker',
        # הלבשה תחתונה
        'men underwear', 'women underwear', 'boxer briefs', 'seamless bra', 'sports bra set',
        'compression socks', 'ankle socks', 'knee high socks',
        # נעלים
        'fashion sneakers', 'casual sneakers', 'slip on shoes', 'loafer shoes',
        'oxford dress shoes', 'ankle boots women', 'knee high boots', 'chelsea boots',
        'platform sandals', 'flip flops beach', 'high heel pumps', 'wedge sandals',
        # בגדי ים
        'bikini set', 'one piece swimsuit', 'swim trunks', 'board shorts', 'rash guard',
        # ביגוד מיוחד
        'plus size dress', 'oversized hoodie', 'streetwear', 'vintage style clothing'
    ]
}


def map_to_category(title, description, aliexpress_category):
    """
    מיפוי חכם לפי כותרת בלבד - Title-First categorization

    עקרונות:
    1. הכותרת מקבלת משקל x5 (הכי חשוב)
    2. קטגוריית AliExpress מקבלת x2 (כללי יותר)
    3. התיאור מקבל x1 (לא משתמשים בו)
    4. ביטויים מרובי מילים מקבלים ניקוד גבוה יותר (יותר ספציפיים)
    5. ברירת מחדל: מוצרי חשמל (לא מוצרים לטלפון)
    """
    title_lower = title.lower()
    aliexpress_cat_lower = aliexpress_category.lower()

    category_scores = {}

    for category, keywords in CATEGORY_MAPPING.items():
        score = 0
        for keyword in keywords:
            kw_lower = keyword.lower()
            word_count = len(kw_lower.split())
            # ניקוד גבוה יותר לביטויים ספציפיים (מרובי מילים)
            phrase_bonus = word_count * 2 if word_count >= 2 else 1

            if kw_lower in title_lower:
                # כותרת = ניקוד גבוה ביותר (x5)
                score += phrase_bonus * 5
            elif kw_lower in aliexpress_cat_lower:
                # קטגוריית AliExpress = ניקוד בינוני (x2)
                score += phrase_bonus * 2

        if score > 0:
            category_scores[category] = score

    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        return best_category

    # ברירת מחדל: מוצרי חשמל (הכי נפוץ ומדויק ברוב המקרים)
    return 'מוצרי חשמל'

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