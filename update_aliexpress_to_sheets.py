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

    # סף ניקוד מינימלי: 15 נקודות
    # ביטוי מילה אחת בכותרת = 5 נקודות (לא מספיק)
    # ביטוי 2 מילים בכותרת = 4×5 = 20 נקודות (מספיק)
    MIN_SCORE = 15

    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] >= MIN_SCORE:
            return best_category

    # ניקוד נמוך מדי / אין התאמה — שונות
    return 'שונות'

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

def find_existing_product(url, title, existing_products):
    """
    מחפש מוצר קיים לפי URL או דמיון כותרת.
    מחזיר את dict המוצר (כולל 'row') אם נמצא, אחרת None.
    """
    title_lower = title.lower()
    for existing in existing_products:
        if url == existing.get('url'):
            return existing
        if len(title_lower) > 10:
            words_new = set(title_lower.split())
            words_existing = set(existing.get('title', '').lower().split())
            if words_new and words_existing:
                similarity = len(words_new & words_existing) / len(words_new | words_existing)
                if similarity > 0.9:
                    return existing
        if title_lower == existing.get('title', '').lower():
            return existing
    return None


def update_prices_in_sheet(price_updates):
    """
    כותב עדכוני מחירים לעמודה I בגוגל שיטס.
    price_updates = list of {'row': int, 'price': float}
    """
    if not price_updates:
        print("  💰 אין עדכוני מחירים להכניס")
        return
    print(f"\n💰 מעדכן {len(price_updates)} מחירים בגיליון (מתוך סריקת hotproduct)...")
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)

        batch_data = [
            {
                'range': f"{SHEET_NAME}!I{item['row']}",
                'values': [[item['price']]]
            }
            for item in price_updates
        ]

        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={'valueInputOption': 'RAW', 'data': batch_data}
        ).execute()

        print(f"  ✅ {len(price_updates)} מחירים עודכנו בהצלחה!")

    except Exception as e:
        print(f"  ❌ שגיאה בעדכון מחירים: {e}")
        import traceback
        traceback.print_exc()


def scan_additional_prices(still_missing_url_to_row):
    """
    סריקה נוספת של hotproduct.query עם sort orders שונים,
    כדי למצוא מחירים למוצרים שלא כוסו בסריקה הראשית.
    מנסה: NEWEST, TRANSACTION_DESC — ללא ship_to_country לכסות מספר גדול יותר של מוצרים.
    still_missing_url_to_row = dict { url: row_number }
    מחזיר list of {'row': int, 'price': float}
    """
    if not still_missing_url_to_row:
        return []

    # בניית מיפוי: product_id → row_number
    pid_to_row = {}
    for url, row in still_missing_url_to_row.items():
        pid = extract_product_id(url)
        if pid:
            pid_to_row[pid] = row

    if not pid_to_row:
        print(f"  ⚠️ לא הצלחתי לחלץ Product IDs מ-{len(still_missing_url_to_row)} URLs")
        return []

    remaining = set(pid_to_row.keys())
    found_prices = []

    # sort orders שונים מהסריקה הראשית — מכסים קטגוריות אחרות
    sort_orders = ['NEWEST', 'TRANSACTION_DESC', 'LAST_VOLUME_DESC']

    print(f"\n🔍 סריקה נוספת: מחפש מחירים ל-{len(remaining)} מוצרים ללא מחיר...")

    for sort_order in sort_orders:
        if not remaining:
            break

        print(f"  📄 סורק עם sort={sort_order} (נשאר {len(remaining)} מוצרים)...")

        for page in range(1, 31):
            if not remaining:
                break

            params = {
                'app_key': str(ALIEXPRESS_APP_KEY),
                'timestamp': str(int(time.time() * 1000)),
                'method': 'aliexpress.affiliate.hotproduct.query',
                'sign_method': 'md5',
                'format': 'json',
                'v': '2.0',
                'page_size': '50',
                'page_no': str(page),
                'sort': sort_order,
                'target_currency': 'USD',
                'target_language': 'EN',
                'tracking_id': str(ALIEXPRESS_TRACKING_ID),
                # ללא ship_to_country — מכסה יותר מוצרים מסוגים שונים
            }

            params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)

            try:
                response = requests.get("https://api-sg.aliexpress.com/sync", params=params, timeout=30)
                data = response.json()

                if 'aliexpress_affiliate_hotproduct_query_response' not in data:
                    print(f"    ⚠️ תגובה לא צפויה בעמוד {page}, עוצר")
                    break

                result = data['aliexpress_affiliate_hotproduct_query_response']['resp_result']
                if result.get('resp_code') != 200:
                    print(f"    ⚠️ resp_code={result.get('resp_code')} — עוצר")
                    break

                products = result.get('result', {}).get('products', {}).get('product', [])
                if not products:
                    break  # אין יותר תוצאות בסדרה זו

                for product in products:
                    pid = str(product.get('product_id', ''))
                    if pid not in remaining:
                        continue
                    price_raw = (product.get('target_sale_price') or
                                 product.get('sale_price') or
                                 product.get('target_original_price') or 0)
                    try:
                        price = round(float(str(price_raw).replace(',', '') or 0), 2)
                        if price > 0:
                            found_prices.append({'row': pid_to_row[pid], 'price': price})
                            remaining.discard(pid)
                    except (ValueError, TypeError):
                        pass

            except Exception as e:
                print(f"    ⚠️ שגיאה בדף {page}: {e}")
                break

            time.sleep(1)

    print(f"  ✅ נמצאו {len(found_prices)} מחירים נוספים | {len(remaining)} עדיין ללא מחיר")
    return found_prices


def fetch_prices_by_product_search(missing_products):
    """
    Fallback אחרון: מחפש מחיר לכל מוצר חסר דרך aliexpress.affiliate.product.query
    (חיפוש לפי מילות מפתח מהכותרת).
    עובד על מוצרים שאינם מופיעים בכלל בתוצאות hotproduct.query.
    missing_products = list of {'url': str, 'row': int, 'title': str}
    מחזיר list of {'row': int, 'price': float}
    """
    if not missing_products:
        return []

    print(f"\n🔎 Keyword search fallback: מחפש מחירים ל-{len(missing_products)} מוצרים...")
    found_prices = []

    for i, item in enumerate(missing_products):
        url   = item.get('url', '')
        row   = item.get('row')
        title = item.get('title', '')
        target_pid = extract_product_id(url)

        if not target_pid or not title or not row:
            continue

        # 5 מילות חיפוש ראשונות (לפחות 3 תווים) מהכותרת
        words = [w for w in title.split() if len(w) >= 3][:5]
        keywords = ' '.join(words)
        if not keywords:
            continue

        try:
            params = {
                'app_key':        str(ALIEXPRESS_APP_KEY),
                'timestamp':      str(int(time.time() * 1000)),
                'method':         'aliexpress.affiliate.product.query',
                'sign_method':    'md5',
                'format':         'json',
                'v':              '2.0',
                'keywords':       keywords,
                'page_size':      '20',
                'page_no':        '1',
                'target_currency':'USD',
                'target_language':'EN',
                'tracking_id':    str(ALIEXPRESS_TRACKING_ID),
            }
            params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)

            response = requests.get("https://api-sg.aliexpress.com/sync", params=params, timeout=20)
            data = response.json()

            result_key = 'aliexpress_affiliate_product_query_response'
            if result_key not in data:
                # הצגת תגובה לאבחון בפעם הראשונה בלבד
                if i == 0:
                    print(f"    ⚠️ מפתח לא צפוי: {list(data.keys())[:3]}")
                continue

            products = (data[result_key]
                        .get('resp_result', {})
                        .get('result', {})
                        .get('products', {})
                        .get('product', []))

            for product in products:
                if str(product.get('product_id', '')) == target_pid:
                    price_raw = (product.get('target_sale_price') or
                                 product.get('sale_price') or
                                 product.get('target_original_price') or 0)
                    try:
                        price = round(float(str(price_raw).replace(',', '') or 0), 2)
                        if price > 0:
                            found_prices.append({'row': row, 'price': price})
                            print(f"    ✅ [{i+1}] ${price} — {title[:45]}")
                    except (ValueError, TypeError):
                        pass
                    break

        except Exception as e:
            print(f"    ⚠️ שגיאה [{i+1}] {title[:30]}: {e}")

        time.sleep(0.5)  # מניעת rate limit

        if (i + 1) % 20 == 0:
            print(f"  📊 התקדמות: {i+1}/{len(missing_products)}, נמצאו {len(found_prices)} עד כה...")

    print(f"  ✅ keyword search: נמצאו {len(found_prices)} | {len(missing_products) - len(found_prices)} ללא מחיר")
    return found_prices


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
            range=f'{SHEET_NAME}!A:I'
        ).execute()

        values = result.get('values', [])

        if not values or len(values) < 2:
            return []

        products = []
        no_price_count = 0
        for i, row in enumerate(values[1:]):
            if len(row) >= 2:
                price_val = row[8] if len(row) > 8 else ''
                try:
                    has_price = bool(price_val and float(str(price_val)) > 0)
                except (ValueError, TypeError):
                    has_price = False
                if not has_price:
                    no_price_count += 1
                products.append({
                    'url': row[0] if len(row) > 0 else '',
                    'title': row[1] if len(row) > 1 else '',
                    'row': i + 2,   # מספר שורה ב-Sheets (1-based, שורה 1 = כותרת)
                    'has_price': has_price
                })

        print(f"Found {len(products)} existing products ({no_price_count} without price)\n")
        return products
        
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

def shorten_with_isgd(long_url):
    """קיצור URL עם is.gd — חינמי ומהיר"""
    try:
        api_url = f"https://is.gd/create.php?format=simple&url={requests.utils.quote(long_url, safe='')}"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            short_url = response.text.strip()
            if short_url.startswith('https://is.gd/') and len(short_url) < 30:
                return short_url
        return ''
    except Exception as e:
        print(f"  ⚠️ Short link failed: {e}")
        return ''


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

        rows = []
        for i, p in enumerate(products):
            affiliate_link = p.get('affiliate_link', '')
            # יצירת Short Link אוטומטית
            short_link = ''
            if affiliate_link:
                print(f"  🔗 Shortening link {i+1}/{len(products)}...")
                short_link = shorten_with_isgd(affiliate_link)
                if short_link:
                    print(f"     ✅ {short_link}")
                time.sleep(0.5)  # מניעת rate limit

            rows.append([
                p.get('url', ''),
                p.get('title', ''),
                p.get('description', ''),
                p.get('image', ''),
                affiliate_link,
                p.get('last_updated', ''),
                p.get('category', 'שונות'),
                short_link,
                p.get('price', '')   # עמודה I - מחיר נוכחי
            ])

        body = {'values': rows}

        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:I',
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"✅ Added {result.get('updates', {}).get('updatedRows', 0)} rows")

    except Exception as e:
        print(f"Error adding products: {e}")
        import traceback
        traceback.print_exc()

def extract_product_id(url):
    """חילוץ Product ID מ-URL של AliExpress — תומך בפורמטים שונים"""
    import re
    if not url:
        return None
    # פורמט רגיל: /item/1005003xxxxxx.html
    match = re.search(r'/item/(\d{10,})', url)
    if match:
        return match.group(1)
    # פורמט קצר: ?productId=xxxxxx
    match = re.search(r'[?&](?:productId|product_id)=(\d{10,})', url)
    if match:
        return match.group(1)
    # פורמט מספרי בסוף URL
    match = re.search(r'(\d{12,})\.html', url)
    if match:
        return match.group(1)
    return None


def fetch_product_prices_batch(product_ids):
    """
    שליפת מחירים עדכניים מ-AliExpress עבור batch של product IDs.
    מחזיר dict: { product_id_str: price_float }
    """
    prices = {}
    try:
        params = {
            'app_key': str(ALIEXPRESS_APP_KEY),
            'timestamp': str(int(time.time() * 1000)),
            'method': 'aliexpress.affiliate.productdetail.get',
            'sign_method': 'md5',
            'format': 'json',
            'v': '2.0',
            'product_ids': ','.join(str(pid) for pid in product_ids),
            'tracking_id': str(ALIEXPRESS_TRACKING_ID),
            'target_currency': 'USD',
            'target_language': 'EN',
            'fields': 'product_id,target_sale_price,sale_price,target_original_price,product_title',
        }
        params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)

        response = requests.get('https://api-sg.aliexpress.com/sync', params=params, timeout=20)
        data = response.json()

        result_key = 'aliexpress_affiliate_productdetail_get_response'
        if result_key not in data:
            # הדפסת התגובה המלאה לאבחון
            print(f"    ⚠️ Unexpected API response keys: {list(data.keys())}")
            # בדיקה אם יש שגיאה מה-API
            error_resp = data.get('error_response', {})
            if error_resp:
                print(f"    ❌ API Error: code={error_resp.get('code')}, msg={error_resp.get('msg')}, sub_msg={error_resp.get('sub_msg', '')}")
            else:
                import json as _json
                print(f"    📋 Full response (first 500 chars): {_json.dumps(data)[:500]}")
            return prices

        result = data[result_key].get('result', {})
        import json as _json

        product_list = result.get('products', {}).get('product', [])

        if not product_list:
            # הצגת ה-result המלא כדי להבין למה אין מוצרים
            print(f"    ⚠️ No products returned. Full result: {_json.dumps(result)[:600]}")
            return prices

        print(f"    ✅ Got {len(product_list)} products from API")

        for product in product_list:
            pid = str(product.get('product_id', ''))
            price_str = (product.get('target_sale_price') or
                         product.get('sale_price') or
                         product.get('target_original_price') or '0')
            try:
                price = float(str(price_str).replace(',', ''))
                if price > 0:
                    prices[pid] = round(price, 2)
            except (ValueError, TypeError):
                pass

        print(f"    💰 Valid prices found: {len(prices)}")

    except Exception as e:
        print(f"    ⚠️ API error in price fetch: {e}")
        import traceback
        traceback.print_exc()

    return prices


def refresh_all_prices():
    """
    מרענן מחירים לכל המוצרים הקיימים בגיליון.
    קורא product IDs מעמודה A, מביא מחירים עדכניים מ-API, כותב לעמודה I.
    """
    print("\n💰 מרענן מחירים עבור כל המוצרים...")

    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)

        # קריאת כל השורות (עמודה A = URL, עמודה I = Price)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:A'
        ).execute()
        rows = result.get('values', [])

        if len(rows) < 2:
            print("  אין מוצרים לרענן")
            return

        # מיפוי row_index → product_id
        to_update = []
        for i, row in enumerate(rows[1:], start=2):  # i = אינדקס שורה בגיליון (מ-2)
            url = row[0] if row else ''
            pid = extract_product_id(url)
            if pid:
                to_update.append({'row': i, 'pid': pid})

        # דיאגנוסטיקה: הצגת 3 URLs ראשונות לבדיקה
        print(f"  📋 דוגמת URLs מהגיליון:")
        for row in rows[1:4]:
            url = row[0] if row else ''
            pid = extract_product_id(url)
            print(f"     URL: {url[:70]}... → ID: {pid}")

        if not to_update:
            print("  ❌ לא נמצאו Product IDs ב-URLs — בדוק שעמודה A מכילה לינקים של AliExpress")
            return

        print(f"  נמצאו {len(to_update)} מוצרים לרענון")

        # עדכון מחירים — batches של 50
        updated = 0
        failed = 0
        BATCH = 50

        for start in range(0, len(to_update), BATCH):
            batch = to_update[start:start + BATCH]
            pids = [b['pid'] for b in batch]

            batch_num = start // BATCH + 1
            print(f"  שולח batch {batch_num} ({len(pids)} מוצרים)...")

            # הדפסת IDs לאבחון (רק batch ראשון)
            if batch_num == 1:
                print(f"    🔍 Sample PIDs: {pids[:5]}")

            prices = fetch_product_prices_batch(pids)

            # אם ה-batch הראשון כבר ריק, אין טעם להמשיך — חסוך API calls
            if batch_num == 1 and not prices:
                print(f"  ⚠️ Batch ראשון החזיר 0 תוצאות — עוצר. בדוק את הלוג למעלה.")
                break

            # כתיבה לגיליון: כל עמודה I בנפרד
            batch_data = []
            for item in batch:
                pid = item['pid']
                if pid in prices:
                    batch_data.append({
                        'range': f"{SHEET_NAME}!I{item['row']}",
                        'values': [[prices[pid]]]
                    })
                    updated += 1
                else:
                    failed += 1

            if batch_data:
                service.spreadsheets().values().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body={'valueInputOption': 'RAW', 'data': batch_data}
                ).execute()

            time.sleep(1)  # מניעת rate limit בין batches

        if updated > 0:
            print(f"  ✅ מחירים עודכנו בהצלחה: {updated} מוצרים")
        else:
            print(f"  ⚠️ לא עודכנו מחירים — ייתכן ש-API productdetail.get אינו זמין לחשבונך")
            print(f"     (המחירים נשמרים בכל זאת בזמן הוספת מוצרים חדשים)")
        if failed > 0:
            print(f"  ℹ️  {failed} מוצרים ללא מחיר (לא הוחזרו מה-API)")

    except Exception as e:
        print(f"  ❌ שגיאה: {e}")
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
        price_updates = []   # עדכוני מחירים למוצרים קיימים
        products_checked = 0
        found_enough_new = False

        for product in products:
            try:
                products_checked += 1

                url = product.get('product_detail_url', '')
                title = product.get('product_title', '')

                if not url or not title:
                    continue

                if not is_quality_product(product):
                    continue

                # חילוץ מחיר לפני בדיקת כפל — כדי לעדכן גם מוצרים קיימים
                try:
                    price_raw = (product.get('target_sale_price') or
                                 product.get('sale_price') or
                                 product.get('target_original_price') or
                                 product.get('original_price') or 0)
                    price = round(float(str(price_raw).replace(',', '') or 0), 2)
                except (ValueError, TypeError):
                    price = 0.0

                # בדיקת כפל — אם קיים, נשמור רק עדכון מחיר
                existing = find_existing_product(url, title, existing_products)
                if existing:
                    if price > 0 and existing.get('row'):
                        price_updates.append({'row': existing['row'], 'price': price})
                    continue

                # מוצר חדש — הוסף רק אם עוד לא הגענו ל-5
                if found_enough_new:
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
                    'category': category,
                    'price': price
                })

                existing_products.append({'url': url, 'title': title, 'row': None})

                price_str = f"${price:.2f}" if price > 0 else "no price"
                print(f"✅ Added ({len(all_new)}): {title[:40]}... → {category} [{price_str}]")

                if len(all_new) >= 5:
                    print(f"\n🎉 Found {len(all_new)} new products! Continuing scan for price updates...")
                    found_enough_new = True

            except Exception as e:
                print(f"  Error: {e}")
                continue

        if all_new:
            print(f"\n✅ Adding {len(all_new)} new products to sheet...")
            add_products_to_sheet(all_new)
        else:
            print("\n⚠️ No new quality products found")

        # עדכון מחירים ממה שנמצא בסריקה
        print(f"\n📊 מחירים שנמצאו בסריקה: {len(price_updates)}")
        update_prices_in_sheet(price_updates)

        # ─── שלב 1: Fallback hotproduct בסדרי מיון שונים ───
        updated_rows = {u['row'] for u in price_updates}
        still_missing_list = [
            {'url': p['url'], 'row': p['row'], 'title': p['title']}
            for p in existing_products
            if p.get('row')
            and p['row'] not in updated_rows
            and not p.get('has_price')   # לא היה מחיר לפני ריצה זו
            and p.get('url')
        ]

        if not still_missing_list:
            print("\n✅ כל המוצרים עודכנו עם מחיר!")
        else:
            # Hotproduct supplementary scan
            still_missing_url_to_row = {item['url']: item['row'] for item in still_missing_list}
            extra_prices = scan_additional_prices(still_missing_url_to_row)
            if extra_prices:
                update_prices_in_sheet(extra_prices)

            # ─── שלב 2: Fallback keyword search ───
            found_rows_extra = {u['row'] for u in extra_prices}
            still_after_scan = [
                item for item in still_missing_list
                if item['row'] not in found_rows_extra
            ]

            if not still_after_scan:
                print("\n✅ כל המוצרים עודכנו עם מחיר!")
            else:
                print(f"\n  ℹ️  {len(still_after_scan)} מוצרים עדיין ללא מחיר — מנסה keyword search...")
                keyword_prices = fetch_prices_by_product_search(still_after_scan)
                if keyword_prices:
                    update_prices_in_sheet(keyword_prices)

                final_missing = len(still_after_scan) - len(keyword_prices)
                if final_missing > 0:
                    print(f"  ⚠️  {final_missing} מוצרים ללא מחיר (ייתכן שהוסרו מ-AliExpress)")
                else:
                    print("\n✅ כל המוצרים עודכנו עם מחיר!")

        print("\n✅ Done!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()