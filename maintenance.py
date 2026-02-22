#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
maintenance.py — סקריפט תחזוקה מלאה
======================================
מטרה: לעבור על כל המוצרים בגיליון ולבצע:
  1. בדיקת HTTP לכל URL — מוצרים עם דף "not found" = נמחקים
  2. עדכון מחיר לכל מוצר חי (target_app_sale_price → הכי מדויק)
  3. fallback מלא: productdetail → link.generate → keyword search
"""

import os, time, re, json, hashlib, requests
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ─── הגדרות ──────────────────────────────────────────────────────────────────
ALIEXPRESS_APP_KEY     = os.environ.get('ALIEXPRESS_APP_KEY')
ALIEXPRESS_APP_SECRET  = os.environ.get('ALIEXPRESS_APP_SECRET')
ALIEXPRESS_TRACKING_ID = 'matan123'
SPREADSHEET_ID         = '1oicbEsS2aU_G698uz-bd6ghUPKx7qt7dLUPFeaa4egU'
SHEET_NAME             = 'Affiliate Table'

# ביטויים שמעידים שהמוצר לא קיים יותר
DEAD_PHRASES = [
    'sorry, the page you requested can not be found',
    'item not found',
    'product not found',
    'page not found',
    'this item is not available',
    'item does not exist',
    'product has been taken off',
    'this product is no longer available',
]

REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# ─── עזרים ───────────────────────────────────────────────────────────────────

def generate_signature(params, secret):
    sorted_params = sorted(params.items())
    sign_string = secret + ''.join(f'{k}{v}' for k, v in sorted_params) + secret
    return hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()


def extract_product_id(url):
    if not url:
        return None
    for pattern in [r'/item/(\d{10,})', r'[?&](?:productId|product_id)=(\d{10,})', r'(\d{12,})\.html']:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def get_service():
    credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    credentials_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict, scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=credentials)


def get_sheet_id(service):
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in spreadsheet.get('sheets', []):
        if sheet['properties']['title'] == SHEET_NAME:
            return sheet['properties']['sheetId']
    return None


# ─── קריאת הגיליון ───────────────────────────────────────────────────────────

def get_all_products(service):
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A:I'
    ).execute()
    rows = result.get('values', [])
    products = []
    for i, row in enumerate(rows[1:], start=2):
        url = row[0] if len(row) > 0 else ''
        if not url:
            continue
        try:
            price = float(str(row[8])) if len(row) > 8 and row[8] else 0
        except Exception:
            price = 0
        products.append({
            'row':   i,
            'url':   url,
            'title': row[1] if len(row) > 1 else '',
            'price': price,
        })
    print(f"📋 נטענו {len(products)} מוצרים מהגיליון")
    return products


# ─── בדיקת קיום URL ───────────────────────────────────────────────────────────

def check_url_alive(url):
    """
    שולח GET ל-AliExpress ובודק אם המוצר עדיין קיים.
    מחזיר True = קיים, False = הוסר.
    """
    pid = extract_product_id(url)
    check_url = f"https://www.aliexpress.com/item/{pid}.html" if pid else url

    try:
        resp = requests.get(check_url, headers=REQUEST_HEADERS, timeout=15, allow_redirects=True)

        # הופנה לעמוד הבית = המוצר הוסר
        final_url = resp.url or ''
        if resp.status_code == 404:
            return False
        if final_url and not re.search(r'/item/\d+', final_url):
            # הRedirect הוביל לדף שאינו מוצר ספציפי
            return False

        content_lower = resp.text.lower()
        for phrase in DEAD_PHRASES:
            if phrase in content_lower:
                return False

        return True

    except requests.exceptions.Timeout:
        return True   # ספק → שמור
    except Exception:
        return True   # ספק → שמור


# ─── שאילת מחיר מה-API ───────────────────────────────────────────────────────

def prices_from_productdetail(pids):
    """
    aliexpress.affiliate.productdetail.get
    מחזיר: { pid: price }, found_pids set
    """
    prices, found_pids = {}, set()
    if not pids:
        return prices, found_pids
    try:
        params = {
            'app_key':       str(ALIEXPRESS_APP_KEY),
            'timestamp':     str(int(time.time() * 1000)),
            'method':        'aliexpress.affiliate.productdetail.get',
            'sign_method':   'md5',
            'format':        'json',
            'v':             '2.0',
            'product_ids':   ','.join(str(p) for p in pids),
            'tracking_id':   ALIEXPRESS_TRACKING_ID,
            'target_currency': 'USD',
            'target_language': 'EN',
            # target_app_sale_price = הנמוך ביותר, הכי קרוב למחיר האמיתי באתר
            'fields': 'product_id,target_app_sale_price,target_sale_price,sale_price,target_original_price',
        }
        params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
        resp = requests.get('https://api-sg.aliexpress.com/sync', params=params, timeout=20)
        data = resp.json()

        key = 'aliexpress_affiliate_productdetail_get_response'
        if key not in data:
            err = data.get('error_response', {})
            print(f"    ⚠️ productdetail.get: {err.get('msg', list(data.keys()))}")
            return prices, found_pids

        product_list = data[key].get('result', {}).get('products', {}).get('product', [])
        for p in product_list:
            pid = str(p.get('product_id', ''))
            found_pids.add(pid)
            raw = (p.get('target_app_sale_price') or p.get('target_sale_price') or
                   p.get('sale_price') or p.get('target_original_price') or '0')
            try:
                price = float(str(raw).replace(',', ''))
                if price > 0:
                    prices[pid] = round(price, 2)
            except Exception:
                pass
    except Exception as e:
        print(f"    ⚠️ productdetail exception: {e}")
    return prices, found_pids


def prices_from_link_generate(url_list):
    """
    aliexpress.affiliate.link.generate
    מחזיר: { url: price }
    """
    out = {}
    BATCH = 12
    for start in range(0, len(url_list), BATCH):
        batch = url_list[start:start + BATCH]
        try:
            params = {
                'app_key':             str(ALIEXPRESS_APP_KEY),
                'timestamp':           str(int(time.time() * 1000)),
                'method':              'aliexpress.affiliate.link.generate',
                'sign_method':         'md5',
                'format':              'json',
                'v':                   '2.0',
                'promotion_link_type': '0',
                'source_values':       ','.join(batch),
                'tracking_id':         ALIEXPRESS_TRACKING_ID,
                'target_currency':     'USD',
            }
            params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
            resp = requests.get('https://api-sg.aliexpress.com/sync', params=params, timeout=20)
            data = resp.json()

            key = 'aliexpress_affiliate_link_generate_response'
            if key not in data:
                continue
            links = (data[key].get('resp_result', {}).get('result', {})
                     .get('promotion_links', {}).get('promotion_link', []))
            for lk in links:
                src = lk.get('source_value', '')
                raw = (lk.get('target_app_sale_price') or lk.get('target_sale_price') or
                       lk.get('sale_price') or 0)
                try:
                    price = float(str(raw).replace(',', '') or '0')
                    if price > 0:
                        out[src] = round(price, 2)
                except Exception:
                    pass
        except Exception as e:
            print(f"    ⚠️ link.generate: {e}")
        time.sleep(1)
    return out


def prices_from_keyword_search(items):
    """
    aliexpress.affiliate.product.query — חיפוש לפי keyword
    items = [{'url', 'title', 'row'}]
    מחזיר: { url: price }
    """
    out = {}
    for i, item in enumerate(items):
        url, title = item['url'], item['title']
        pid = extract_product_id(url)
        words = title.lower().split()

        def search(keyword, max_pages=2):
            for page in range(1, max_pages + 1):
                try:
                    params = {
                        'app_key':         str(ALIEXPRESS_APP_KEY),
                        'timestamp':       str(int(time.time() * 1000)),
                        'method':          'aliexpress.affiliate.product.query',
                        'sign_method':     'md5',
                        'format':          'json',
                        'v':               '2.0',
                        'keywords':        keyword,
                        'page_no':         str(page),
                        'page_size':       '40',
                        'sort':            'SALE_PRICE_ASC',
                        'tracking_id':     ALIEXPRESS_TRACKING_ID,
                        'target_currency': 'USD',
                        'fields':          'product_id,target_app_sale_price,target_sale_price,sale_price',
                    }
                    params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
                    resp = requests.get('https://api-sg.aliexpress.com/sync', params=params, timeout=20)
                    data = resp.json()
                    rkey = 'aliexpress_affiliate_product_query_response'
                    if rkey not in data:
                        break
                    result = data[rkey].get('resp_result', {})
                    if isinstance(result.get('resp_code'), str):
                        result = json.loads(result['resp_code'])
                    products_raw = result.get('result', {}).get('products', {}).get('product', [])
                    for p in products_raw:
                        if str(p.get('product_id', '')) == str(pid):
                            raw = (p.get('target_app_sale_price') or p.get('target_sale_price') or
                                   p.get('sale_price') or 0)
                            try:
                                price = float(str(raw).replace(',', ''))
                                if price > 0:
                                    return price
                            except Exception:
                                pass
                    time.sleep(0.5)
                except Exception:
                    pass
            return None

        kw1 = ' '.join(words[:5])
        price = search(kw1, 3)
        if price is None and len(words) > 3:
            price = search(' '.join(words[1:5]), 2)
        if price is None and pid:
            price = search(pid, 1)

        if price:
            out[url] = price
            print(f"    ✅ [{i+1}] ${price} — {title[:45]}")
        else:
            print(f"    ❌ [{i+1}] ללא מחיר — {title[:45]}")

        if (i + 1) % 5 == 0:
            time.sleep(2)

    return out


# ─── כתיבה לגיליון ────────────────────────────────────────────────────────────

def write_prices(service, price_list):
    """price_list = [{'row': int, 'price': float}]"""
    if not price_list:
        return
    data = [{'range': f"{SHEET_NAME}!I{item['row']}", 'values': [[item['price']]]}
            for item in price_list]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={'valueInputOption': 'RAW', 'data': data}
    ).execute()
    print(f"  ✅ נכתבו {len(price_list)} מחירים לגיליון")


def delete_rows(service, sheet_id, row_indices):
    if not row_indices:
        return 0
    sorted_rows = sorted(set(row_indices), reverse=True)
    reqs = [{
        'deleteDimension': {
            'range': {
                'sheetId':    sheet_id,
                'dimension':  'ROWS',
                'startIndex': r - 1,
                'endIndex':   r
            }
        }
    } for r in sorted_rows]
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={'requests': reqs}
    ).execute()
    return len(sorted_rows)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("🔧 MAINTENANCE — סריקה מלאה")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("❌ Missing API keys")
        return

    service   = get_service()
    products  = get_all_products(service)
    sheet_id  = get_sheet_id(service)

    # ════════════════════════════════════════════════════════════════
    # שלב 1 — בדיקת קיום HTTP לכל מוצר
    # ════════════════════════════════════════════════════════════════
    print(f"\n🔍 שלב 1 — בדיקת קיום {len(products)} מוצרים...")
    alive, dead_rows = [], []
    DELAY = 1.2   # שניות בין בקשות (מניעת rate-limit)

    for i, p in enumerate(products):
        is_alive = check_url_alive(p['url'])
        label    = "✅" if is_alive else "❌ מת"
        print(f"  [{i+1:>3}/{len(products)}] {label} — {p['title'][:50]}")

        if is_alive:
            alive.append(p)
        else:
            dead_rows.append(p['row'])

        if (i + 1) % 20 == 0:
            print(f"  📊 {i+1}/{len(products)} | חיים={len(alive)} | מתים={len(dead_rows)}")

        time.sleep(DELAY)

    print(f"\n📊 שלב 1 תוצאות: {len(alive)} חיים | {len(dead_rows)} מתים")

    if dead_rows and sheet_id:
        deleted = delete_rows(service, sheet_id, dead_rows)
        print(f"🗑️ נמחקו {deleted} מוצרים מהגיליון")
    elif dead_rows:
        print(f"⚠️ לא ניתן למחוק שורות — sheetId לא נמצא")

    # ════════════════════════════════════════════════════════════════
    # שלב 2 — עדכון מחיר לכל המוצרים החיים
    # ════════════════════════════════════════════════════════════════
    print(f"\n💰 שלב 2 — מחירים עבור {len(alive)} מוצרים")
    price_updates = []     # [{'row', 'price'}]
    no_price      = []     # מוצרים שעדיין ללא מחיר אחרי productdetail
    BATCH         = 50

    # ── 2a: productdetail.get (API הדיוק הגבוה ביותר) ──────────────
    print("\n  📡 2a: aliexpress.affiliate.productdetail.get ...")
    pid_map          = {}    # pid → product
    no_pid_products  = []

    for p in alive:
        pid = extract_product_id(p['url'])
        if pid:
            pid_map[pid] = p
        else:
            no_pid_products.append(p)

    all_pids     = list(pid_map.keys())
    api_working  = None   # None=לא ידוע, True=עובד, False=לא זמין

    for start in range(0, len(all_pids), BATCH):
        batch_pids = all_pids[start:start + BATCH]
        batch_num  = start // BATCH + 1
        print(f"    batch {batch_num} ({len(batch_pids)} מוצרים)...")

        prices, found = prices_from_productdetail(batch_pids)

        if api_working is None:
            api_working = bool(found)
            if api_working:
                print(f"    ✅ productdetail.get עובד!")
            else:
                print(f"    ⚠️ productdetail.get לא זמין — עובר ישר ל-link.generate")
                no_price = alive   # כל המוצרים יטופלו בשלב הבא
                break

        for pid, price in prices.items():
            p = pid_map.get(pid)
            if p:
                price_updates.append({'row': p['row'], 'price': price})

        for pid in batch_pids:
            if pid not in found:
                p = pid_map.get(pid)
                if p:
                    no_price.append(p)

        time.sleep(1)

    # מוצרים ללא product_id
    no_price.extend(no_pid_products)

    # ── 2b: link.generate fallback ──────────────────────────────────
    if no_price:
        print(f"\n  🔗 2b: link.generate — {len(no_price)} מוצרים...")
        url_list   = [p['url'] for p in no_price]
        lg_prices  = prices_from_link_generate(url_list)

        still_no_price = []
        for p in no_price:
            price = lg_prices.get(p['url'])
            if price:
                price_updates.append({'row': p['row'], 'price': price})
            else:
                still_no_price.append(p)

        print(f"    ✅ link.generate: {len(no_price) - len(still_no_price)} מחירים")
        no_price = still_no_price

    # ── 2c: keyword search fallback (אחרון) ──────────────────────────
    if no_price:
        print(f"\n  🔎 2c: keyword search — {len(no_price)} מוצרים...")
        kw_prices = prices_from_keyword_search(no_price)

        final_no_price = []
        for p in no_price:
            price = kw_prices.get(p['url'])
            if price:
                price_updates.append({'row': p['row'], 'price': price})
            else:
                final_no_price.append(p)

        no_price = final_no_price

    # ── כתיבה לגיליון ──────────────────────────────────────────────
    print(f"\n📝 כותב {len(price_updates)} מחירים לגיליון...")
    write_prices(service, price_updates)

    # ════════════════════════════════════════════════════════════════
    # סיכום
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("📊 סיכום:")
    print(f"  🔍 סה\"כ מוצרים שנבדקו: {len(products)}")
    print(f"  🗑️  מוצרים שנמחקו (מתים): {len(dead_rows)}")
    print(f"  ✅ מוצרים חיים: {len(alive)}")
    print(f"  💰 מחירים שעודכנו: {len(price_updates)}")
    if no_price:
        print(f"  ⚠️  ללא מחיר (API לא מאנדקס): {len(no_price)}")
        for p in no_price:
            print(f"       — {p['title'][:60]}")
    else:
        print(f"  🎉 כל המוצרים עודכנו עם מחיר!")
    print("\n✅ Done!")


if __name__ == '__main__':
    main()
