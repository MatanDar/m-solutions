#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
M-SOLUTIONS - מיון מחדש של כל המוצרים בגיליון
Recategorize All Products - Title-First Smart Categorization
============================================================

הסקריפט קורא את כל המוצרים מ-Google Sheets,
ממיין אותם מחדש לפי הכותרת (Title) בלבד,
ומעדכן את עמודת CATEGORY בטבלה.

הפעלה:
  python3 recategorize_all_products.py

דרישות:
  - משתנה סביבה GOOGLE_SHEETS_CREDENTIALS עם ה-JSON של Service Account
  - או קובץ google_sheets_credentials.json בתיקייה הנוכחית
"""

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# ============ הגדרות ============
SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME = 'Affiliate Table'

# עמודות: A=URL, B=Title, C=Description, D=Image, E=AffiliateLink, F=LastUpdated, G=Category, H=ShortLink
COL_TITLE = 1        # עמודה B (אינדקס 1)
COL_CATEGORY = 6     # עמודה G (אינדקס 6)

# ============ מיפוי קטגוריות - Title-First ============
# ביטויים מרובי מילים = יותר ספציפיים = ניקוד גבוה יותר
CATEGORY_MAPPING = {
    'מוצרים לטלפון': [
        'phone case', 'iphone case', 'samsung case', 'phone cover', 'phone skin', 'back cover',
        'screen protector', 'tempered glass', 'glass protector', 'privacy glass',
        'selfie stick', 'selfie ring', 'phone grip', 'phone ring holder', 'finger ring holder',
        'phone holder', 'phone mount', 'car mount', 'car phone mount', 'phone stand',
        'phone dock', 'phone wallet case', 'phone strap', 'phone pouch',
        'power bank', 'wireless charger', 'magsafe', 'magnetic charger', 'charging pad',
        'earbuds', 'airpods', 'tws', 'true wireless', 'in-ear headphone',
        'lightning cable', 'lightning charger', 'for iphone', 'for ipad',
        'for samsung galaxy', 'for android phone', 'for xiaomi', 'for huawei',
        'phone lens', 'phone camera lens', 'clip on lens',
        'iphone', 'ipad', 'airpods',
        'mobile phone', 'smartphone', 'android phone', 'cell phone'
    ],
    'מוצרי חשמל': [
        'smart home', 'smart plug', 'smart switch', 'smart bulb', 'smart light',
        'smart lamp', 'smart socket', 'alexa compatible', 'google home',
        'security camera', 'ip camera', 'wifi camera', 'cctv', 'nvr system', 'dvr system',
        'outdoor camera', 'indoor camera', 'baby monitor',
        'robot vacuum', 'vacuum cleaner', 'robotic vacuum', 'cordless vacuum',
        'air conditioner', 'portable ac', 'air cooler', 'cooling fan',
        'electric fan', 'tower fan', 'ceiling fan', 'bladeless fan',
        'air purifier', 'humidifier', 'dehumidifier', 'air diffuser', 'essential oil diffuser',
        'led strip', 'led light strip', 'strip light', 'neon light', 'rgb light',
        'desk lamp', 'floor lamp', 'table lamp', 'bedside lamp', 'led bulb', 'smart bulb',
        'led grow light', 'grow light',
        'projector', 'mini projector', 'portable projector', 'home projector',
        'dash cam', 'dashcam', 'action camera', 'body camera', 'car recorder',
        'bluetooth speaker', 'portable speaker', 'soundbar', 'sound bar',
        'wireless speaker', 'outdoor speaker', 'desktop speaker',
        'smart watch', 'smartwatch', 'fitness band', 'fitness tracker', 'smart band',
        'gps watch', 'sport watch',
        'electric kettle', 'electric razor', 'electric shaver', 'electric toothbrush',
        'hair dryer', 'hair straightener', 'curling iron', 'hair curler', 'epilator',
        'face massager', 'skin care device',
        'usb hub', 'usb splitter', 'power strip', 'extension cord', 'surge protector',
        'voltage tester', 'multimeter', 'clamp meter', 'soldering iron', 'heat gun', 'hot glue gun',
        'battery charger', 'solar panel', 'solar charger', 'power inverter',
        'drone', 'quadcopter', 'fpv drone', 'rc drone', 'aerial drone',
        'smart tv', 'tv box', 'android tv box', 'media player', 'hdmi switch',
        'electric scooter', 'e-scooter', 'electric bicycle', 'e-bike', 'electric skateboard',
        'hover board'
    ],
    'מטבח ובית': [
        'kitchen', 'cooking', 'baking', 'frying pan', 'sauce pan', 'wok pan', 'pot set',
        'knife set', 'cutting board', 'chopping board', 'peeler', 'grater', 'colander',
        'spatula', 'ladle', 'silicone tongs', 'whisk', 'rolling pin', 'pizza cutter',
        'food container', 'lunch box', 'food storage', 'mason jar', 'vacuum seal',
        'meal prep container', 'bento box', 'airtight container',
        'coffee maker', 'coffee grinder', 'french press', 'tea infuser', 'pour over',
        'blender', 'juicer', 'toaster oven', 'waffle maker', 'sandwich maker', 'egg cooker',
        'rice cooker', 'slow cooker', 'instant pot', 'pressure cooker',
        'dish rack', 'dish drying rack', 'kitchen organizer', 'spice rack', 'spice jar',
        'drawer organizer', 'cabinet organizer', 'pot rack',
        'toilet brush', 'shower curtain', 'soap dispenser', 'bath mat set',
        'bathroom organizer', 'toilet paper holder', 'shower caddy',
        'laundry bag', 'clothes hanger', 'drying rack', 'ironing board', 'lint roller',
        'mop set', 'broom dustpan', 'cleaning brush', 'scrub sponge', 'microfiber towel',
        'bed sheet set', 'pillow case', 'throw blanket', 'quilt cover', 'duvet cover', 'mattress topper',
        'tablecloth', 'placemats', 'coaster set', 'candle holder',
        'picture frame', 'wall sticker', 'wall art print', 'wall clock', 'planter pot',
        'doormat', 'bath mat', 'area rug', 'chair cushion', 'sofa cover', 'throw pillow',
        'dinnerware set', 'plate set', 'bowl set', 'ceramic mug', 'wine glass', 'cutlery set'
    ],
    'ספורט וכושר': [
        'yoga mat', 'resistance band', 'pull up bar', 'push up board', 'ab roller wheel',
        'jump rope', 'skipping rope', 'dumbbell set', 'kettlebell', 'barbell', 'weight plate',
        'gym gloves', 'weightlifting belt', 'knee sleeve', 'knee brace',
        'wrist wrap', 'ankle support', 'elbow brace', 'compression sleeve',
        'running shoes', 'trail running', 'hiking boots', 'cycling shoes', 'tennis shoes',
        'sports bra', 'gym shorts', 'compression leggings', 'athletic wear',
        'running jacket', 'track suit',
        'soccer ball', 'basketball', 'volleyball', 'tennis racket', 'badminton racket',
        'table tennis paddle', 'ping pong', 'golf club', 'golf ball',
        'swimming goggles', 'swim cap', 'wetsuit', 'diving mask', 'snorkel set',
        'camping tent', 'sleeping bag', 'hiking backpack', 'trekking pole', 'camping stove',
        'camping lantern', 'survival kit', 'carabiner', 'hammock',
        'bike helmet', 'cycling gloves', 'cycling jersey', 'bike light', 'bike lock',
        'boxing gloves', 'punching bag', 'mma gloves', 'kick boxing',
        'yoga block', 'yoga strap', 'foam roller', 'pilates ring', 'stretching band'
    ],
    'תיקים ואביזרים': [
        'backpack', 'school bag', 'laptop backpack', 'shoulder bag', 'crossbody bag',
        'messenger bag', 'sling bag', 'fanny pack', 'waist bag', 'belt bag',
        'tote bag', 'handbag', 'clutch purse', 'evening bag', 'work tote',
        'travel bag', 'duffel bag', 'gym bag', 'weekender bag', 'diaper bag', 'camera bag',
        'wallet', 'card holder', 'money clip', 'coin purse', 'passport wallet',
        'rfid wallet', 'slim wallet', 'leather wallet', 'bifold wallet',
        'luggage set', 'suitcase', 'carry on bag', 'travel organizer', 'packing cube',
        'necklace', 'pendant necklace', 'bracelet', 'earrings', 'stud earrings',
        'anklet', 'charm bracelet', 'statement necklace', 'ring jewelry',
        'sunglasses', 'reading glasses', 'blue light glasses', 'eyeglass frame',
        'baseball cap', 'trucker hat', 'beanie hat', 'bucket hat', 'sun hat', 'snapback',
        'hair band', 'scrunchie', 'hair clip', 'hair accessory', 'headband',
        'leather belt', 'watch band', 'watch strap', 'apple watch band', 'smartwatch band'
    ],
    'כלי עבודה': [
        'screwdriver set', 'wrench set', 'combination pliers', 'claw hammer', 'hand saw',
        'hex key set', 'allen wrench', 'socket wrench', 'torque wrench', 'adjustable spanner',
        'measuring tape', 'laser level', 'spirit level', 'laser distance', 'digital caliper',
        'angle finder', 'protractor',
        'utility knife', 'box cutter', 'wire stripper', 'crimping tool', 'cable cutter', 'pipe cutter',
        'electric drill', 'cordless drill', 'drill bit set', 'impact driver', 'rotary tool',
        'jigsaw', 'circular saw', 'angle grinder', 'belt sander', 'orbital sander',
        'tool set', 'hand tool kit', 'tool box', 'tool bag', 'tool organizer',
        'flashlight', 'headlamp', 'work light', 'tactical flashlight', 'torch',
        'step ladder', 'extension ladder', 'folding ladder', 'telescoping ladder',
        'safety glasses', 'work gloves', 'ear muffs', 'dust mask', 'n95 mask', 'face shield',
        'car jack', 'floor jack', 'jump starter', 'tire inflator', 'oil filter wrench',
        'automotive tool', 'car repair', 'obd scanner',
        'cable tie', 'zip tie', 'hose clamp', 'sandpaper', 'grinding wheel', 'cutting wheel'
    ],
    'צעצועים': [
        'lego set', 'building blocks', 'wooden blocks', 'magnetic tiles', 'construction set',
        'jigsaw puzzle', '3d puzzle', 'wooden puzzle', 'floor puzzle',
        'remote control car', 'rc car', 'rc truck', 'rc robot', 'rc helicopter', 'rc boat',
        'toy car set', 'toy truck', 'toy train set', 'diecast model', 'die cast car',
        'action figure', 'anime figure', 'model kit', 'gundam',
        'doll house', 'baby doll', 'plush toy', 'stuffed animal', 'teddy bear', 'plush unicorn',
        'fidget spinner', 'pop it', 'stress relief toy', 'sensory toy', 'kinetic sand',
        'slime kit', 'play doh set', 'diy craft kit', 'paint set for kids',
        'board game', 'card game', 'chess set', 'tabletop game',
        'kite flying', 'water gun toy', 'bubble machine', 'lawn game',
        'educational toy', 'montessori toy', 'stem kit', 'science kit',
        'kids bicycle', 'balance bike', 'kids kick scooter', 'ride on toy', 'push car'
    ],
    'אופנה': [
        't-shirt', 'graphic tee', 'polo shirt', 'dress shirt', 'blouse', 'crop top', 'tank top',
        'jeans', 'denim pants', 'chino pants', 'cargo trousers', 'jogger pants', 'wide leg pants',
        'midi dress', 'maxi dress', 'mini dress', 'floral dress', 'bodycon dress',
        'a-line skirt', 'mini skirt', 'pleated skirt',
        'denim jacket', 'leather jacket', 'varsity jacket', 'bomber jacket',
        'hoodie sweatshirt', 'zip up hoodie', 'cardigan sweater', 'knit sweater',
        'down puffer jacket', 'winter parka', 'trench coat', 'overcoat', 'windbreaker jacket',
        'men underwear', 'women underwear', 'boxer briefs', 'seamless bra',
        'compression socks', 'ankle socks', 'knee high socks',
        'fashion sneakers', 'casual sneakers', 'slip on shoes', 'loafer shoes',
        'oxford dress shoes', 'ankle boots women', 'knee high boots', 'chelsea boots',
        'platform sandals', 'flip flops beach', 'high heel pumps', 'wedge sandals',
        'bikini set', 'one piece swimsuit', 'swim trunks', 'board shorts', 'rash guard',
        'plus size dress', 'oversized hoodie', 'streetwear', 'vintage style clothing'
    ]
}

VALID_CATEGORIES = list(CATEGORY_MAPPING.keys())


def categorize_by_title(title: str, aliexpress_category: str = '') -> tuple[str, int]:
    """
    מיין לפי כותרת בלבד.
    מחזיר (קטגוריה, ניקוד).
    ביטויים מרובי מילים = ניקוד גבוה יותר.
    """
    title_lower = title.lower().strip()
    cat_lower = aliexpress_category.lower().strip()

    scores = {}
    for category, keywords in CATEGORY_MAPPING.items():
        score = 0
        for keyword in keywords:
            kw_lower = keyword.lower()
            word_count = len(kw_lower.split())
            phrase_bonus = word_count * 2 if word_count >= 2 else 1

            if kw_lower in title_lower:
                score += phrase_bonus * 5   # כותרת = ניקוד גבוה ביותר
            elif kw_lower in cat_lower:
                score += phrase_bonus * 2   # קטגוריית AliExpress

        if score > 0:
            scores[category] = score

    if scores:
        best = max(scores, key=scores.get)
        return best, scores[best]

    return 'מוצרי חשמל', 0  # ברירת מחדל - לא מוצרים לטלפון!


def get_google_sheets_service():
    """יצירת חיבור ל-Google Sheets"""
    # נסה קודם מ-environment variable
    credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')

    if not credentials_json:
        # נסה מקובץ מקומי
        cred_file = os.path.join(os.path.dirname(__file__), 'google_sheets_credentials.json')
        if os.path.exists(cred_file):
            with open(cred_file, 'r') as f:
                credentials_json = f.read()
        else:
            raise Exception(
                "❌ לא נמצאו פרטי הזדהות!\n"
                "הגדר GOOGLE_SHEETS_CREDENTIALS כמשתנה סביבה\n"
                "או מקם google_sheets_credentials.json בתיקייה"
            )

    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=credentials)


def main():
    print("=" * 65)
    print("🔧 M-SOLUTIONS - מיון מחדש של כל המוצרים (Title-First)")
    print("=" * 65)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 גיליון: {SPREADSHEET_ID}")
    print(f"📋 שלייט: {SHEET_NAME}")
    print("=" * 65)

    # התחברות ל-Google Sheets
    print("\n🔌 מתחבר ל-Google Sheets...")
    service = get_google_sheets_service()
    print("✅ חיבור הצליח!")

    # קריאת כל הנתונים
    print(f"\n📥 קורא נתונים מ-{SHEET_NAME}...")
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A:H'
    ).execute()

    values = result.get('values', [])
    if not values or len(values) < 2:
        print("⚠️ לא נמצאו נתונים בגיליון!")
        return

    headers = values[0]
    rows = values[1:]
    print(f"✅ נמצאו {len(rows)} מוצרים")

    # מיון מחדש
    print("\n🔧 מתחיל מיון מחדש לפי כותרת...")
    print("-" * 65)

    updates = []  # (row_index, new_category, old_category, title, score)
    category_stats = {cat: 0 for cat in VALID_CATEGORIES}
    no_change = 0
    errors = 0

    for i, row in enumerate(rows):
        try:
            # חילוץ נתונים (עם טיפול בשורות חסרות)
            title = row[COL_TITLE].strip() if len(row) > COL_TITLE and row[COL_TITLE] else ''
            old_category = row[COL_CATEGORY].strip() if len(row) > COL_CATEGORY and row[COL_CATEGORY] else ''

            if not title:
                continue

            # מיון חדש לפי כותרת
            new_category, score = categorize_by_title(title)

            if new_category != old_category:
                updates.append((i + 2, new_category, old_category, title, score))  # +2 כי שורה 1 = כותרות
                print(f"  ✏️ שורה {i+2}: {title[:45]}...")
                print(f"     ❌ {old_category or 'ללא'} → ✅ {new_category} (ניקוד: {score})")

            category_stats[new_category] = category_stats.get(new_category, 0) + 1

        except Exception as e:
            errors += 1
            print(f"  ❌ שגיאה בשורה {i+2}: {e}")

    print("-" * 65)
    print(f"\n📊 סיכום מיון:")
    print(f"   🔄 מוצרים לעדכון: {len(updates)}")
    print(f"   ✅ ללא שינוי: {len(rows) - len(updates) - errors}")
    if errors:
        print(f"   ❌ שגיאות: {errors}")

    print(f"\n📈 התפלגות קטגוריות חדשה:")
    for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"   {cat}: {count} מוצרים")

    if not updates:
        print("\n✅ כל המוצרים כבר ממוינים נכון! אין מה לעדכן.")
        return

    # אישור לפני עדכון
    print(f"\n⚠️  עומד לעדכן {len(updates)} מוצרים ב-Google Sheets")
    confirm = input("האם להמשיך? (y/n): ").strip().lower()

    if confirm != 'y':
        print("❌ הופסק על ידי המשתמש.")
        return

    # עדכון Google Sheets
    print(f"\n📤 מעדכן {len(updates)} שורות ב-Google Sheets...")

    # קיבוץ עדכונים לbatch אחד (יעיל יותר)
    batch_data = []
    for row_num, new_category, old_category, title, score in updates:
        batch_data.append({
            'range': f'{SHEET_NAME}!G{row_num}',
            'values': [[new_category]]
        })

    # שליחה ב-batches של 100 בכל פעם
    BATCH_SIZE = 100
    total_updated = 0

    for start in range(0, len(batch_data), BATCH_SIZE):
        batch = batch_data[start:start + BATCH_SIZE]
        body = {
            'valueInputOption': 'RAW',
            'data': batch
        }
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
        total_updated += len(batch)
        print(f"  ✅ עודכנו {total_updated}/{len(updates)} שורות...")

    print(f"\n🎉 הושלם! עודכנו {total_updated} מוצרים בהצלחה!")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    print("💡 טיפ: רענן את האתר כדי לראות את הקטגוריות החדשות!")
    print("=" * 65)


if __name__ == '__main__':
    main()
