#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
maintenance.py — סקריפט תחזוקה מלאה (גרסה 2 — ללא HTTP check)
================================================================
לוגיקה:
  שלב 1 — productdetail.get על כל המוצרים
           • מוצר שה-API מחזיר → חי → שמרו + עדכנו מחיר
           • מוצר שה-API לא מחזיר → מת → מחקו מהגיליון
           • אם ה-API מחזיר 0 תוצאות בסה"כ → API שבור, אל תמחק כלום

  שלב 2 — מוצרים חיים ללא מחיר → link.generate

  שלב 3 — עדיין ללא מחיר → keyword search

  ⚠️  HTTP check הוסר לחלוטין — AliExpress חוסמת בקשות מ-proxy/datacenter
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
API_BATCH_SIZE         = 50   # מקסימום product_ids לפנייה אחת ל-productdetail.get


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


# ─── productdetail.get ────────────────────────────────────────────────────────

def productdetail_batch(pids):
    """
    שולח פנייה ל-aliexpress.affiliate.productdetail.get
    מחזיר: ( {pid: price}, found_pids_set )
    """
    prices, found_pids = {}, set()
    if not pids:
        return prices, found_pids
    try:
        params = {
            'app_key':         str(ALIEXPRESS_APP_KEY),
            'timestamp':       str(int(time.time() * 1000)),
            'method':          'aliexpress.affiliate.productdetail.get',
            'sign_method':     'md5',
            'format':          'json',
            'v':               '2.0',
            'product_ids':     ','.join(str(p) for p in pids),
            'tracking_id':     ALIEXPRESS_TRACKING_ID,
            'target_currency': 'USD',
            'target_language': 'EN',
            'fields':          'product_id,target_app_sale_price,target_sale_price,sale_price,target_original_price',
        }
        params['sign'] = generate_signature(params, ALIEXPRESS_APP_SECRET)
        resp = requests.get('https://api-sg.aliexpress.com/sync', params=params, timeout=25)
        data = resp.json()

        key = 'aliexpress_affiliate_productdetail_get_response'
        if key not in data:
            err = data.get('error_response', {})
            print(f"    ⚠️  productdetail.get error: {err.get('msg', list(data.keys()))}")
            return prices, found_pids

        product_list = (data[key]
                        .get('result', {})
                        .get('products', {})
                        .get('product', []))

        for p in product_list:
            pid = str(p.get('product_id', ''))
            if not pid:
                continue
            found_pids.add(pid)
            raw = (p.get('target_app_sale_price') or
                   p.get('target_sale_price') or
                   p.get('sale_price') or
                   p.get('target_original_price') or '0')
            try:
                price = float(str(raw).replace(',', ''))
                if price > 0:
                    prices[pid] = round(price, 2)
            except Exception:
                pass

    except Exception as e:
        print(f"    ⚠️  productdetail exception: {e}")

    return prices, found_pids


# ─── link.generate fallback ───────────────────────────────────────────────────

def prices_from_link_generate(url_list):
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
            links = (data[key]
                     .get('resp_result', {})
                     .get('result', {})
                     .get('promotion_links', {})
                     .get('promotion_link', []))
            for lk in links:
                src = lk.get('source_value', '')
                raw = (lk.get('target_app_sale_price') or
                       lk.get('target_sale_price') or
                       lk.get('sale_price') or 0)
                try:
                    price = float(str(raw).replace(',', '') or '0')
                    if price > 0:
                        out[src] = round(price, 2)
                except Exception:
                    pass
        except Exception as e:
            print(f"    ⚠️  link.generate: {e}")
        time.sleep(1)
    return out


# ─── keyword search fallback ──────────────────────────────────────────────────

def prices_from_keyword_search(items):
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
                    products_raw = result.get('result', {}).get('products', {}).get('product', [])
                    for p in products_raw:
                        if str(p.get('product_id', '')) == str(pid):
                            raw = (p.get('target_app_sale_price') or
                                   p.get('target_sale_price') or
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
            print(f"    ✅ [{i+1}] ${price:.2f} — {title[:45]}")
        else:
            print(f"    ❌ [{i+1}] ללא מחיר — {title[:45]}")

        if (i + 1) % 5 == 0:
            time.sleep(2)

    return out


# ─── כתיבה לגיליון ────────────────────────────────────────────────────────────

def write_prices(service, price_list):
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
    print("🔧 MAINTENANCE v2 — productdetail.get based dead-product detection")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    if not ALIEXPRESS_APP_KEY or not ALIEXPRESS_APP_SECRET:
        print("❌ Missing API keys — set ALIEXPRESS_APP_KEY and ALIEXPRESS_APP_SECRET")
        return

    service  = get_service()
    products = get_all_products(service)
    sheet_id = get_sheet_id(service)

    if not products:
        print("⚠️  אין מוצרים בגיליון")
        return

    # ────────────────────────────────────────────────────────────────
    # שלב 1 — productdetail.get על כל המוצרים
    #   • מוצר שמוחזר מ-API → חי
    #   • מוצר שלא מוחזר   → מת → מחק מהגיליון
    #   • אם ה-API מחזיר 0 תוצאות בסה"כ → API לא זמין → אל תמחק כלום
    # ────────────────────────────────────────────────────────────────
    print(f"\n🔍 שלב 1 — productdetail.get עבור {len(products)} מוצרים...")

    pid_map         = {}   # pid → product dict
    no_pid_products = []   # מוצרים שלא ניתן לחלץ מהם product_id

    for p in products:
        pid = extract_product_id(p['url'])
        if pid:
            pid_map[pid] = p
        else:
            no_pid_products.append(p)

    print(f"  🔑 {len(pid_map)} מוצרים עם product_id | {len(no_pid_products)} ללא")

    all_pids          = list(pid_map.keys())
    total_found       = set()   # כל ה-pid שה-API הכיר
    price_updates     = []      # [{'row', 'price'}]
    api_returned_any  = False   # האם ה-API עבד בכלל?

    for start in range(0, len(all_pids), API_BATCH_SIZE):
        batch_pids = all_pids[start:start + API_BATCH_SIZE]
        batch_num  = start // API_BATCH_SIZE + 1
        total_batches = (len(all_pids) + API_BATCH_SIZE - 1) // API_BATCH_SIZE
        print(f"  📡 batch {batch_num}/{total_batches} ({len(batch_pids)} מוצרים)...", end=' ', flush=True)

        prices, found = productdetail_batch(batch_pids)

        if found:
            api_returned_any = True
        total_found |= found

        for pid, price in prices.items():
            p = pid_map.get(pid)
            if p:
                price_updates.append({'row': p['row'], 'price': price})

        print(f"→ {len(found)}/{len(batch_pids)} נמצאו | {len(prices)} עם מחיר")
        time.sleep(1.2)

    # ── זיהוי מוצרים מתים ─────────────────────────────────────────
    dead_rows    = []
    alive_no_pid = []   # מוצרים ללא pid — לא נוכל לבדוק, נשאיר

    if not api_returned_any:
        print("\n  ⚠️  productdetail.get לא החזיר שום תוצאה — API כנראה שבור")
        print("  🛡️  ביטחון: לא מוחקים שום מוצר כדי לא לאבד נתונים")
        # במצב זה נעביר הכל ל-link.generate
        no_price_after_detail = list(pid_map.values()) + no_pid_products
    else:
        # כל pid שלא הוחזר = מת
        dead_pids = set(all_pids) - total_found
        for pid in dead_pids:
            p = pid_map[pid]
            dead_rows.append(p['row'])
            print(f"  💀 מת: {p['title'][:55]} (pid={pid})")

        # מוצרים חיים ללא מחיר → שלב 2
        priced_rows = {pu['row'] for pu in price_updates}
        no_price_after_detail = [
            p for pid, p in pid_map.items()
            if pid in total_found and p['row'] not in priced_rows
        ] + no_pid_products

    print(f"\n  📊 תוצאות שלב 1:")
    print(f"     ✅ חיים: {len(total_found)}")
    print(f"     💀 מתים: {len(dead_rows)}")
    print(f"     💰 עם מחיר: {len(price_updates)}")
    print(f"     ❓ חיים ללא מחיר: {len(no_price_after_detail)}")

    # ── מחיקת מוצרים מתים ─────────────────────────────────────────
    if dead_rows and sheet_id:
        print(f"\n🗑️  מוחק {len(dead_rows)} מוצרים מתים מהגיליון...")
        deleted = delete_rows(service, sheet_id, dead_rows)
        print(f"  ✅ נמחקו {deleted} שורות")
    elif dead_rows:
        print(f"  ⚠️  לא ניתן למחוק שורות — sheetId לא נמצא")

    # ────────────────────────────────────────────────────────────────
    # שלב 2 — link.generate עבור מוצרים חיים ללא מחיר
    # ────────────────────────────────────────────────────────────────
    no_price_after_link = []

    if no_price_after_detail:
        print(f"\n🔗 שלב 2 — link.generate עבור {len(no_price_after_detail)} מוצרים...")
        url_list  = [p['url'] for p in no_price_after_detail]
        lg_prices = prices_from_link_generate(url_list)

        for p in no_price_after_detail:
            price = lg_prices.get(p['url'])
            if price:
                price_updates.append({'row': p['row'], 'price': price})
            else:
                no_price_after_link.append(p)

        print(f"  ✅ link.generate: {len(no_price_after_detail) - len(no_price_after_link)} מחירים")

    # ────────────────────────────────────────────────────────────────
    # שלב 3 — keyword search כ-fallback אחרון
    # ────────────────────────────────────────────────────────────────
    final_no_price = []

    if no_price_after_link:
        print(f"\n🔎 שלב 3 — keyword search עבור {len(no_price_after_link)} מוצרים...")
        kw_prices = prices_from_keyword_search(no_price_after_link)

        for p in no_price_after_link:
            price = kw_prices.get(p['url'])
            if price:
                price_updates.append({'row': p['row'], 'price': price})
            else:
                final_no_price.append(p)

    # ── כתיבת מחירים ──────────────────────────────────────────────
    print(f"\n📝 כותב {len(price_updates)} מחירים לגיליון...")
    write_prices(service, price_updates)

    # ════════════════════════════════════════════════════════════════
    # סיכום
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 65)
    print("📊 סיכום סופי:")
    print(f"  🔍 סה\"כ מוצרים שנבדקו : {len(products)}")
    print(f"  🗑️  נמחקו (מוצרים מתים): {len(dead_rows)}")
    print(f"  ✅ מוצרים חיים         : {len(total_found) + len(no_pid_products)}")
    print(f"  💰 מחירים שעודכנו     : {len(price_updates)}")

    if final_no_price:
        print(f"  ⚠️  ללא מחיר (API לא מאנדקס): {len(final_no_price)}")
        for p in final_no_price:
            print(f"       — {p['title'][:60]}")
    else:
        print("  🎉 כל המוצרים החיים עודכנו עם מחיר!")

    print("\n✅ Done!")


if __name__ == '__main__':
    main()
