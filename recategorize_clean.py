#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recategorize_clean.py
=====================
1. קורא את כל המוצרים מ-Google Sheets
2. מסווג מחדש כל מוצר לפי CATEGORY_MAPPING (identically to update_aliexpress_to_sheets.py)
3. מוחק מוצרים ללא מחיר (price = 0 or empty)
4. כותב את הקטגוריות המעודכנות לגיליון

הפעלה: python recategorize_clean.py
"""

import os, json, hashlib, time
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ─── הגדרות ──────────────────────────────────────────────────────────────────
SPREADSHEET_ID = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME     = 'Affiliate Table'

# עמודות (0-indexed):
# A=0 URL | B=1 Title | C=2 Description | D=3 Image | E=4 Affiliate Link
# F=5 Last Updated | G=6 CATEGORY | H=7 Short Link | I=8 Price

COL_URL         = 0
COL_TITLE       = 1
COL_DESCRIPTION = 2
COL_CATEGORY    = 6
COL_PRICE       = 8

# ─── CATEGORY MAPPING (זהה ל-update_aliexpress_to_sheets.py) ─────────────────
CATEGORY_MAPPING = {
    'מוצרים לטלפון': [
        'phone case', 'iphone case', 'samsung case', 'phone cover', 'phone skin', 'back cover',
        'screen protector', 'tempered glass', 'glass protector', 'privacy glass',
        'selfie stick', 'selfie ring', 'phone grip', 'phone ring holder', 'finger ring holder',
        'phone holder', 'phone mount', 'car mount', 'car phone mount', 'phone stand',
        'phone dock', 'phone wallet case', 'phone strap', 'phone pouch', 'phone tripod',
        'power bank', 'wireless charger', 'magsafe', 'magnetic charger', 'charging pad',
        'car charger', 'type c charger', 'usb c charger', 'fast charger cable',
        'type c cable', 'usb c cable', 'usb-c cable', 'lightning cable', 'lightning charger',
        'charging cable', 'data cable', 'phone cable', 'type-c cable',
        'earbuds', 'airpods', 'tws earphone', 'true wireless', 'in-ear headphone',
        'bluetooth earphone', 'wireless earbuds', 'sports earphone',
        'type c adapter', 'usb c adapter', 'otg adapter', 'usb otg',
        'for iphone', 'for ipad', 'for samsung galaxy', 'for android phone',
        'for xiaomi', 'for huawei', 'for oneplus',
        'phone lens', 'phone camera lens', 'clip on lens', 'selfie light',
        'clip lens', 'fisheye lens',
        'ring light', 'selfie ring light', 'mini ring light',
        'iphone', 'ipad', 'airpods',
        'mobile phone', 'smartphone', 'android phone', 'cell phone',
    ],
    'מוצרי חשמל': [
        'smart home', 'smart plug', 'smart switch', 'smart bulb', 'smart light',
        'smart lamp', 'smart socket', 'wifi smart', 'smart doorbell', 'smart sensor',
        'motion sensor', 'door sensor', 'alexa compatible', 'google home',
        'security camera', 'ip camera', 'wifi camera', 'cctv', 'nvr system', 'dvr system',
        'outdoor camera', 'indoor camera', 'baby monitor', 'nanny cam',
        'robot vacuum', 'vacuum cleaner', 'robotic vacuum', 'cordless vacuum',
        'handheld vacuum', 'wet dry vacuum',
        'air conditioner', 'portable ac', 'air cooler', 'cooling fan', 'electric fan',
        'tower fan', 'ceiling fan', 'bladeless fan', 'desk fan', 'table fan',
        'mini fan', 'neck fan', 'portable fan', 'usb fan',
        'air purifier', 'humidifier', 'dehumidifier', 'air diffuser', 'essential oil diffuser',
        'aroma diffuser',
        'led strip', 'led light strip', 'strip light', 'neon light', 'rgb light', 'rgb strip',
        'desk lamp', 'floor lamp', 'table lamp', 'bedside lamp', 'led bulb', 'smart bulb',
        'led grow light', 'grow light', 'night light lamp', 'led night light',
        'monitor light', 'screen light bar', 'monitor bar', 'led bar light',
        'projector', 'mini projector', 'portable projector', 'home projector', 'home theater',
        'dash cam', 'dashcam', 'action camera', 'body camera', 'car recorder',
        'web camera', 'webcam', 'pc camera',
        'bluetooth speaker', 'portable speaker', 'soundbar', 'sound bar',
        'wireless speaker', 'outdoor speaker', 'desktop speaker', 'mini speaker',
        'wireless headphones', 'bluetooth headphones', 'gaming headset', 'over ear headphones',
        'on ear headphones', 'noise cancelling headphones', 'noise canceling headphones',
        'headphone with mic', 'studio headphones', 'foldable headphones',
        'smart watch', 'smartwatch', 'fitness band', 'fitness tracker', 'smart band',
        'gps watch', 'sport watch', 'health monitor', 'activity tracker',
        'massage gun', 'neck massager', 'back massager', 'foot massager', 'electric massager',
        'blood pressure monitor', 'pulse oximeter', 'digital thermometer', 'body thermometer',
        'heating pad', 'electric heating', 'tens machine', 'ems machine',
        'facial steamer', 'face steamer', 'led face mask', 'skin care device',
        'electric kettle', 'electric razor', 'electric shaver', 'electric toothbrush',
        'hair dryer', 'hair straightener', 'curling iron', 'hair curler', 'epilator',
        'face massager', 'hair trimmer', 'beard trimmer', 'nose hair trimmer',
        'electric nail drill', 'nail drill machine',
        'gaming mouse', 'wireless mouse', 'optical mouse', 'bluetooth mouse', 'computer mouse',
        'gaming keyboard', 'mechanical keyboard', 'wireless keyboard', 'bluetooth keyboard',
        'rgb keyboard', 'rgb mouse', 'gaming controller', 'game controller', 'gamepad controller',
        'laptop stand', 'laptop cooler', 'laptop cooling pad', 'cooling pad', 'laptop riser',
        'mouse pad', 'gaming mouse pad', 'extended mouse pad', 'desk mat',
        'usb hub', 'usb splitter', 'usb dock', 'docking station', 'type c hub',
        'hdmi cable', 'hdmi adapter', 'hdmi switch', 'dp cable', 'displayport cable',
        'vga cable', 'usb extension cable',
        'power strip', 'extension cord', 'surge protector', 'usb power strip',
        'wall charger', 'usb wall charger', 'fast charger', 'quick charger', 'pd charger',
        'power adapter', 'ac adapter', 'charging station', 'charging dock',
        'voltage tester', 'multimeter', 'clamp meter', 'soldering iron', 'heat gun', 'hot glue gun',
        'battery charger', 'aa battery charger', 'solar panel', 'solar charger', 'power inverter',
        'drone', 'quadcopter', 'fpv drone', 'rc drone', 'aerial drone', 'mini drone',
        'smart tv', 'tv box', 'android tv box', 'media player', 'streaming stick',
        'digital frame', 'photo frame digital', 'digital photo frame',
        'steam mop', 'steam cleaner', 'steam iron', 'electric steam',
        'electric scooter', 'e-scooter', 'electric bicycle', 'e-bike', 'electric skateboard',
        'hoverboard', 'hover board', 'self balancing',
    ],
    'מטבח ובית': [
        'kitchen', 'cooking', 'baking', 'frying pan', 'sauce pan', 'wok pan', 'pot set',
        'knife set', 'cutting board', 'chopping board', 'peeler', 'grater', 'colander',
        'spatula', 'ladle', 'silicone tongs', 'whisk', 'rolling pin', 'pizza cutter',
        'kitchen gadget', 'cooking tool', 'kitchen tool',
        'food container', 'lunch box', 'food storage', 'mason jar', 'vacuum seal',
        'meal prep container', 'bento box', 'airtight container',
        'coffee maker', 'coffee grinder', 'french press', 'tea infuser', 'pour over',
        'blender', 'juicer', 'toaster oven', 'waffle maker', 'sandwich maker', 'egg cooker',
        'rice cooker', 'slow cooker', 'instant pot', 'pressure cooker',
        'dish rack', 'dish drying rack', 'kitchen organizer', 'spice rack', 'spice jar',
        'drawer organizer', 'cabinet organizer', 'pot rack', 'shelf organizer',
        'storage box', 'storage organizer', 'storage bin', 'organizer box', 'desk organizer',
        'closet organizer', 'wardrobe organizer', 'clothes organizer', 'storage rack',
        'shoe rack', 'shoe organizer', 'shoe box', 'shoe storage', 'shoe shelf',
        'cable management', 'cable organizer', 'cable box', 'wire organizer',
        'toilet brush', 'shower curtain', 'soap dispenser', 'bath mat set',
        'bathroom organizer', 'toilet paper holder', 'shower caddy', 'bathroom shelf',
        'laundry bag', 'laundry basket', 'laundry hamper', 'clothes hanger', 'drying rack',
        'ironing board', 'lint roller', 'mop set', 'broom dustpan', 'cleaning brush',
        'scrub sponge', 'microfiber towel', 'microfiber cloth', 'cleaning cloth',
        'garbage bag', 'trash bag', 'bin liner', 'trash can', 'waste bin', 'rubbish bin',
        'bed sheet set', 'pillow case', 'throw blanket', 'quilt cover', 'duvet cover',
        'mattress topper', 'memory foam pillow', 'sleep mask', 'eye mask sleep',
        'tablecloth', 'placemats', 'coaster set', 'candle holder', 'picture frame',
        'wall sticker', 'wall art print', 'wall clock', 'planter pot', 'flower vase',
        'doormat', 'bath mat', 'area rug', 'chair cushion', 'sofa cover', 'throw pillow',
        'curtain rod', 'curtain hooks', 'home decoration', 'home decor', 'room decor',
        'dinnerware set', 'plate set', 'bowl set', 'ceramic mug', 'wine glass', 'cutlery set',
    ],
    'ספורט וכושר': [
        'yoga mat', 'resistance band', 'pull up bar', 'push up board', 'ab roller wheel',
        'jump rope', 'skipping rope', 'dumbbell set', 'kettlebell', 'barbell', 'weight plate',
        'gym gloves', 'weightlifting belt', 'knee sleeve', 'knee brace',
        'wrist wrap', 'ankle support', 'elbow brace', 'compression sleeve',
        'running shoes', 'trail running', 'hiking boots', 'cycling shoes', 'tennis shoes',
        'sports bra', 'gym shorts', 'compression leggings', 'athletic wear',
        'running jacket', 'wind breaker running', 'track suit',
        'soccer ball', 'basketball', 'volleyball', 'tennis racket', 'badminton racket',
        'table tennis paddle', 'ping pong', 'golf club', 'golf ball',
        'swimming goggles', 'swim cap', 'wetsuit', 'diving mask', 'snorkel set',
        'camping tent', 'sleeping bag', 'hiking backpack', 'trekking pole', 'camping stove',
        'camping lantern', 'survival kit', 'carabiner', 'hammock',
        'bike helmet', 'cycling gloves', 'cycling jersey', 'bike light', 'bike lock',
        'boxing gloves', 'punching bag', 'mma gloves', 'kick boxing',
        'yoga block', 'yoga strap', 'foam roller', 'pilates ring', 'stretching band',
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
        'leather belt', 'watch band', 'watch strap', 'apple watch band', 'smartwatch band',
    ],
    'כלי עבודה': [
        'screwdriver set', 'wrench set', 'combination pliers', 'claw hammer', 'hand saw',
        'hex key set', 'allen wrench', 'socket wrench', 'torque wrench', 'adjustable spanner',
        'adjustable wrench', 'socket set', 'hex key', 'allen key',
        'measuring tape', 'laser level', 'spirit level', 'laser distance', 'digital caliper',
        'angle finder', 'protractor',
        'utility knife', 'box cutter', 'wire stripper', 'crimping tool', 'cable cutter', 'pipe cutter',
        'electric drill', 'cordless drill', 'drill bit set', 'drill bit', 'impact driver',
        'electric screwdriver', 'rotary tool', 'jigsaw', 'circular saw', 'angle grinder',
        'belt sander', 'orbital sander',
        'tool set', 'hand tool kit', 'tool box', 'tool bag', 'tool organizer',
        'flashlight', 'headlamp', 'work light', 'tactical flashlight', 'led torch',
        'step ladder', 'extension ladder', 'folding ladder', 'telescoping ladder',
        'safety glasses', 'work gloves', 'ear muffs', 'dust mask', 'n95 mask', 'face shield',
        'car jack', 'floor jack', 'jump starter', 'tire inflator', 'oil filter wrench',
        'automotive tool', 'car repair', 'obd scanner',
        'cable tie', 'zip tie', 'hose clamp', 'sandpaper', 'grinding wheel', 'cutting wheel',
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
        'board game', 'card game', 'chess set', 'monopoly style', 'tabletop game',
        'kite flying', 'water gun toy', 'bubble machine', 'lawn game',
        'educational toy', 'montessori toy', 'stem kit', 'science kit',
        'kids bicycle', 'balance bike', 'kids kick scooter', 'ride on toy', 'push car',
    ],
    'אופנה': [
        't-shirt', 'graphic tee', 'polo shirt', 'dress shirt', 'blouse', 'crop top', 'tank top',
        'jeans', 'denim pants', 'chino pants', 'cargo trousers', 'jogger pants', 'wide leg pants',
        'midi dress', 'maxi dress', 'mini dress', 'floral dress', 'bodycon dress',
        'a-line skirt', 'mini skirt', 'pleated skirt',
        'denim jacket', 'leather jacket', 'varsity jacket', 'bomber jacket',
        'hoodie sweatshirt', 'zip up hoodie', 'cardigan sweater', 'knit sweater',
        'down puffer jacket', 'winter parka', 'trench coat', 'overcoat', 'windbreaker',
        'men underwear', 'women underwear', 'boxer briefs', 'seamless bra', 'sports bra set',
        'compression socks', 'ankle socks', 'knee high socks',
        'fashion sneakers', 'casual sneakers', 'slip on shoes', 'loafer shoes',
        'oxford dress shoes', 'ankle boots women', 'knee high boots', 'chelsea boots',
        'platform sandals', 'flip flops beach', 'high heel pumps', 'wedge sandals',
        'bikini set', 'one piece swimsuit', 'swim trunks', 'board shorts', 'rash guard',
        'plus size dress', 'oversized hoodie', 'streetwear', 'vintage style clothing',
    ],
}

VALID_CATEGORIES = set(CATEGORY_MAPPING.keys()) | {'שונות'}
MIN_SCORE = 15  # זהה ל-Python


def map_to_category(title: str, aliexpress_category: str = '') -> str:
    """
    מסווג מוצר לפי כותרת.
    זהה לפונקציה ב-update_aliexpress_to_sheets.py.
    """
    title_lower = title.lower()
    ali_lower   = aliexpress_category.lower()

    scores = {}
    for category, keywords in CATEGORY_MAPPING.items():
        score = 0
        for kw in keywords:
            kw_lower    = kw.lower()
            word_count  = len(kw_lower.split())
            phrase_bonus = word_count * 2 if word_count >= 2 else 1

            if kw_lower in title_lower:
                score += phrase_bonus * 5
            elif kw_lower in ali_lower:
                score += phrase_bonus * 2

        if score > 0:
            scores[category] = score

    if scores:
        best = max(scores, key=scores.get)
        if scores[best] >= MIN_SCORE:
            return best

    return 'שונות'


# ─── Google Sheets helpers ────────────────────────────────────────────────────

def get_service():
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        raise RuntimeError('GOOGLE_SHEETS_CREDENTIALS not set')
    creds_dict  = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=credentials)


def get_sheet_id(service):
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == SHEET_NAME:
            return sheet['properties']['sheetId']
    raise RuntimeError(f"Sheet '{SHEET_NAME}' not found")


def read_all_rows(service):
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A:I'
    ).execute()
    return result.get('values', [])


def delete_rows_by_index(service, sheet_id, row_indices):
    """מוחק שורות לפי אינדקס שורה בגיליון (1-indexed). מוחק בסדר הפוך."""
    if not row_indices:
        return 0
    reqs = [{
        'deleteDimension': {
            'range': {
                'sheetId':    sheet_id,
                'dimension':  'ROWS',
                'startIndex': r - 1,
                'endIndex':   r
            }
        }
    } for r in sorted(set(row_indices), reverse=True)]
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={'requests': reqs}
    ).execute()
    return len(reqs)


def write_category_updates(service, updates):
    """updates = [{'row': int, 'category': str}]  — כותב לעמודה G"""
    if not updates:
        return
    data = [
        {'range': f"{SHEET_NAME}!G{u['row']}", 'values': [[u['category']]]}
        for u in updates
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={'valueInputOption': 'RAW', 'data': data}
    ).execute()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    from datetime import datetime
    print("🔧 RECATEGORIZE + CLEAN — סיווג מחדש + ניקוי ללא מחיר")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    service  = get_service()
    sheet_id = get_sheet_id(service)
    rows     = read_all_rows(service)

    if not rows or len(rows) < 2:
        print("⚠️  הגיליון ריק")
        return

    header   = rows[0]
    products = rows[1:]  # without header
    print(f"📋 סה\"כ {len(products)} מוצרים בגיליון")

    # ────────────────────────────────────────────────────────────────
    # שלב 1 — מחיקת מוצרים ללא מחיר
    # ────────────────────────────────────────────────────────────────
    print("\n🗑️  שלב 1 — איתור מוצרים ללא מחיר...")
    no_price_rows = []

    for i, row in enumerate(products):
        sheet_row = i + 2  # row index in sheet (1-indexed, header=1)
        price_raw = row[COL_PRICE] if len(row) > COL_PRICE else ''
        try:
            price = float(str(price_raw).replace(',', '').strip()) if price_raw else 0.0
        except Exception:
            price = 0.0

        if price <= 0:
            title = row[COL_TITLE] if len(row) > COL_TITLE else ''
            no_price_rows.append(sheet_row)
            print(f"  ❌ ללא מחיר [שורה {sheet_row}]: {title[:60]}")

    if no_price_rows:
        print(f"\n  מוחק {len(no_price_rows)} מוצרים ללא מחיר...")
        deleted = delete_rows_by_index(service, sheet_id, no_price_rows)
        print(f"  ✅ נמחקו {deleted} שורות")
        # Re-read after deletion
        rows     = read_all_rows(service)
        products = rows[1:]
        print(f"  📋 {len(products)} מוצרים נותרו לאחר מחיקה")
    else:
        print("  ✅ כל המוצרים כבר עם מחיר — אין מה למחוק")

    # ────────────────────────────────────────────────────────────────
    # שלב 2 — סיווג מחדש
    # ────────────────────────────────────────────────────────────────
    print("\n🏷️  שלב 2 — סיווג מחדש של כל המוצרים...")

    cat_updates  = []
    changed      = 0
    unchanged    = 0
    cat_dist     = {}  # קטגוריה → כמות

    for i, row in enumerate(products):
        sheet_row    = i + 2
        title        = row[COL_TITLE]       if len(row) > COL_TITLE       else ''
        description  = row[COL_DESCRIPTION] if len(row) > COL_DESCRIPTION else ''
        old_category = row[COL_CATEGORY]    if len(row) > COL_CATEGORY    else ''

        new_category = map_to_category(title, description)

        cat_dist[new_category] = cat_dist.get(new_category, 0) + 1

        if new_category != old_category:
            cat_updates.append({'row': sheet_row, 'category': new_category})
            changed += 1
            print(f"  🔄 [{sheet_row}] {old_category!r} → {new_category!r}   {title[:50]}")
        else:
            unchanged += 1

    print(f"\n  📊 {changed} שינויים, {unchanged} ללא שינוי")

    if cat_updates:
        print(f"  ✍️  כותב {len(cat_updates)} עדכוני קטגוריה...")
        write_category_updates(service, cat_updates)
        print("  ✅ עדכוני קטגוריה נשמרו")

    # ── סיכום קטגוריות ──────────────────────────────────────────────
    print("\n📊 פילוג קטגוריות לאחר עדכון:")
    for cat, count in sorted(cat_dist.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")

    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 65)
    print("✅ Done!")
    print(f"   מחוקו: {len(no_price_rows)} | שונו קטגוריות: {changed}")


if __name__ == '__main__':
    main()
