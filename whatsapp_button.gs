/**
 * ============================================================
 * M-SOLUTIONS Google Sheets Script - גרסה מאוחדת
 * ============================================================
 *
 * כולל:
 *   ✅ מיון חכם לקטגוריות (מבוסס כותרת - אנגלית!)
 *   ✅ קיצור לינקים עם is.gd
 *   ✅ כפתור WhatsApp - שליחת מוצר יומי לקבוצה
 *   ✅ עריכה אוטומטית (onEdit)
 *   ✅ שליפת נתוני מוצר מ-AliExpress
 *
 * HOW TO INSTALL:
 * ─────────────────────────────────────────────────────────
 * 1. פתח Extensions → Apps Script
 * 2. מחק את כל הקוד הישן והדבק קוד זה
 * 3. שמור (Ctrl+S)
 * 4. לכפתור WhatsApp: Insert → Drawing → צייר כפתור
 *    → שמור → 3 נקודות → Assign script → sendWhatsAppProduct
 * ─────────────────────────────────────────────────────────
 */


// ============================================================
// הגדרות גלובליות
// ============================================================

const SHEET_NAME = 'Affiliate Table';

// עמודות: A=URL, B=Title, C=Description, D=Image,
//          E=AffiliateLink, F=LastUpdated, G=Category, H=ShortLink, I=Price
const COL = {
  URL: 0,
  TITLE: 1,
  DESCRIPTION: 2,
  IMAGE: 3,
  AFFILIATE_LINK: 4,
  LAST_UPDATED: 5,
  CATEGORY: 6,
  SHORT_LINK: 7,
  PRICE: 8
};


// ============================================================
// מיון קטגוריות — מילות מפתח באנגלית (כי הכותרות מ-AliExpress הן באנגלית!)
// ⚠️  חשוב: הקטגוריות חייבות להתאים בדיוק לשמות ב-index.html ו-update_aliexpress_to_sheets.py
// ============================================================

const CATEGORY_KEYWORDS = {
  'מוצרים לטלפון': [
    'phone case', 'iphone case', 'samsung case', 'phone cover', 'back cover',
    'screen protector', 'tempered glass', 'glass protector',
    'earbuds', 'earphone', 'earbud', 'headphone', 'headset',
    'airpods', 'tws', 'wireless earphone',
    'power bank', 'powerbank', 'portable charger', 'wireless charger',
    'phone charger', 'fast charger', 'usb charger',
    'charging cable', 'usb cable', 'lightning cable', 'type-c cable', 'type c cable',
    'phone stand', 'phone holder', 'car phone holder', 'car mount',
    'selfie stick', 'selfie ring', 'ring light',
    'phone lens', 'camera lens',
    'pop socket', 'popsocket', 'phone grip', 'phone ring',
    'for iphone', 'for samsung', 'for xiaomi', 'for huawei', 'for oppo',
    'iphone 15', 'iphone 14', 'iphone 13', 'iphone 12', 'iphone 11',
    'samsung galaxy', 'galaxy s',
    'mobile phone', 'smartphone accessory',
    'sim card', 'memory card', 'sd card', 'micro sd'
  ],

  'מוצרי חשמל': [
    'smart home', 'smart plug', 'smart switch', 'smart bulb', 'smart lamp',
    'security camera', 'cctv', 'ip camera', 'surveillance', 'doorbell camera',
    'robot vacuum', 'robotic vacuum', 'robot mop', 'vacuum cleaner',
    'led strip', 'led light', 'led lamp', 'led bulb', 'rgb light', 'neon light',
    'projector', 'mini projector', 'home theater',
    'bluetooth speaker', 'portable speaker', 'wireless speaker', 'speaker',
    'smartwatch', 'smart watch', 'fitness tracker', 'fitness band', 'smart band',
    'drone', 'quadcopter', 'fpv drone',
    'electric fan', 'desk fan', 'portable fan', 'air purifier', 'humidifier',
    'electric kettle', 'coffee maker', 'air fryer', 'instant pot', 'rice cooker',
    'hair dryer', 'hair straightener', 'hair curler', 'electric shaver', 'trimmer',
    'solar panel', 'solar charger',
    'raspberry pi', 'arduino', 'esp32',
    'printer', '3d printer', 'label printer',
    'monitor', 'keyboard', 'mouse', 'webcam', 'microphone',
    'gaming headset', 'gaming mouse', 'gaming keyboard',
    'hard drive', 'ssd', 'usb hub', 'usb adapter',
    'extension cord', 'power strip', 'surge protector'
  ],

  'מטבח ובית': [
    'kitchen', 'cookware', 'cooking',
    'pot', 'pan', 'frying pan', 'wok', 'saucepan', 'casserole',
    'knife', 'kitchen knife', 'chef knife', 'cutting board', 'chopping board',
    'plate', 'bowl', 'cup', 'mug', 'glass', 'dish',
    'food container', 'lunch box', 'bento box', 'storage container',
    'blender', 'juicer', 'mixer',
    'coffee', 'coffee cup', 'coffee mug', 'french press', 'moka pot',
    'tea', 'teapot', 'tea infuser',
    'oven mitt', 'apron', 'kitchen glove',
    'strainer', 'colander', 'grater', 'peeler', 'can opener',
    'spatula', 'ladle', 'whisk', 'tongs',
    'baking', 'baking pan', 'baking mold', 'cake mold',
    'shelving', 'shelf', 'storage rack', 'organizer',
    'hanger', 'clothes hanger', 'laundry basket',
    'curtain', 'rug', 'carpet', 'mat',
    'pillow', 'cushion', 'blanket', 'bedding', 'bed sheet', 'duvet',
    'towel', 'bath towel',
    'cleaning', 'mop', 'broom', 'scrubber', 'sponge',
    'soap dispenser', 'toothbrush holder', 'toilet brush',
    'wall clock', 'picture frame', 'photo frame',
    'candle', 'aroma', 'diffuser', 'air freshener',
    'home decor', 'decoration', 'ornament', 'figurine'
  ],

  'ספורט וכושר': [
    'sport', 'sports', 'fitness', 'workout', 'exercise', 'training', 'gym',
    'yoga', 'yoga mat', 'pilates', 'meditation',
    'dumbbell', 'barbell', 'weight', 'kettlebell', 'resistance band',
    'jump rope', 'skipping rope', 'pull up bar',
    'running', 'jogging', 'marathon', 'cycling', 'bicycle', 'bike',
    'swimming', 'swim', 'goggles', 'swim cap',
    'football', 'soccer', 'basketball', 'tennis', 'badminton', 'volleyball',
    'boxing', 'martial arts', 'karate',
    'skateboard', 'scooter', 'roller skate',
    'hiking', 'camping', 'outdoor', 'climbing',
    'water bottle', 'sport bottle', 'shaker bottle', 'protein shaker',
    'compression', 'sport socks', 'sport gloves', 'helmet',
    'foam roller', 'massage gun', 'muscle roller',
    'treadmill', 'stationary bike', 'rowing machine'
  ],

  'תיקים ואביזרים': [
    'bag', 'handbag', 'backpack', 'rucksack', 'tote bag', 'shoulder bag',
    'crossbody bag', 'satchel', 'messenger bag',
    'wallet', 'purse', 'card holder', 'money clip',
    'laptop bag', 'laptop backpack', 'computer bag',
    'travel bag', 'duffel bag', 'gym bag', 'sports bag',
    'luggage', 'suitcase', 'trolley bag', 'luggage cover',
    'cosmetic bag', 'makeup bag', 'toiletry bag',
    'pencil case', 'school bag', 'student bag',
    'key chain', 'keychain', 'key holder', 'key ring',
    'umbrella', 'sunglasses case', 'glasses case'
  ],

  'כלי עבודה': [
    // כלי יד — ספציפיים בלבד
    'tool set', 'tool kit', 'hand tool', 'power tool',
    'screwdriver set', 'screwdriver bit', 'electric screwdriver',
    'cordless drill', 'electric drill', 'drill bit', 'drill press',
    'impact driver', 'impact wrench',
    'claw hammer', 'rubber mallet', 'sledge hammer',
    'adjustable wrench', 'torque wrench', 'socket wrench', 'wrench set',
    'combination pliers', 'needle nose pliers', 'locking pliers',
    'wire cutter', 'cable cutter', 'pipe cutter', 'bolt cutter',
    'jigsaw', 'circular saw', 'reciprocating saw', 'hand saw',
    'angle grinder', 'bench grinder', 'belt sander', 'orbital sander',
    // מדידה — ספציפי
    'measuring tape', 'tape measure',
    'spirit level', 'laser level', 'bubble level',
    'digital caliper', 'vernier caliper', 'laser distance',
    // ארגון כלים
    'toolbox', 'tool box', 'tool bag', 'tool organizer', 'tool chest',
    // חשמל ואלקטרוניקה
    'soldering iron', 'soldering station', 'heat gun', 'hot glue gun',
    'multimeter', 'voltage tester', 'wire stripper', 'crimping tool',
    // בטיחות עבודה
    'safety glasses', 'work gloves', 'ear muffs', 'dust mask', 'face shield',
    // רכב
    'car jack', 'floor jack', 'jump starter', 'tire inflator',
    'obd scanner', 'automotive tool', 'car repair tool',
    // עבודות גינה ובנייה
    'step ladder', 'extension ladder', 'folding ladder',
    'sandpaper', 'grinding disc', 'cutting disc', 'abrasive pad',
    'cable tie', 'zip tie', 'hose clamp'
  ],

  'צעצועים': [
    'toy', 'toys', 'children', 'child', 'kids', 'baby', 'toddler', 'infant',
    'doll', 'action figure', 'stuffed animal', 'plush', 'teddy bear',
    'lego', 'building blocks', 'block set', 'construction toy',
    'puzzle', 'jigsaw puzzle',
    'remote control car', 'rc car', 'rc truck', 'rc toy', 'toy car',
    'toy drone', 'mini drone',
    'board game', 'card game', 'chess', 'checkers',
    'play dough', 'kinetic sand', 'slime',
    'drawing set', 'coloring book', 'art set', 'craft kit',
    'sticker', 'bubble', 'balloon',
    'baby toy', 'baby rattle', 'teether',
    'playground', 'swing', 'slide',
    'water gun', 'nerf', 'foam dart'
  ],

  'אופנה': [
    't-shirt', 'tshirt', 'shirt', 'blouse', 'top',
    'pants', 'trousers', 'jeans', 'leggings', 'shorts',
    'dress', 'skirt', 'jumpsuit', 'romper',
    'jacket', 'coat', 'hoodie', 'sweater', 'sweatshirt', 'cardigan',
    'suit', 'blazer', 'vest',
    'shoes', 'sneakers', 'boots', 'sandals', 'flip flops', 'slippers',
    'socks', 'stockings', 'tights', 'leggings',
    'underwear', 'bra', 'lingerie', 'swimsuit', 'bikini',
    'hat', 'cap', 'beanie', 'bucket hat',
    'gloves', 'mittens', 'scarf', 'shawl',
    'sunglasses', 'eyeglasses frame',
    'watch', 'bracelet', 'necklace', 'earring', 'ring', 'anklet',
    'belt', 'tie', 'bow tie',
    'fashion', 'clothing', 'apparel', 'outfit',
    'winter wear', 'summer wear', 'activewear', 'sportswear',
    'plus size', 'maternity'
  ]
};


// ============================================================
// פונקציית מיון חכמה — כותרת ראשונה (x5), תיאור (x1)
// זהה בדיוק ללוגיקה ב-update_aliexpress_to_sheets.py וב-index.html
// ============================================================

function smartCategorize(title, description) {
  const titleLower = (title || '').toLowerCase().trim();
  const descLower = (description || '').toLowerCase().trim();

  const scores = {};

  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    let score = 0;

    for (const keyword of keywords) {
      const kw = keyword.toLowerCase();
      const wordCount = kw.trim().split(/\s+/).length;
      const phraseBonus = wordCount >= 2 ? wordCount * 2 : 1;

      if (titleLower.includes(kw)) {
        score += phraseBonus * 5;       // כותרת = ×5
      } else if (descLower.includes(kw)) {
        score += phraseBonus * 1;       // תיאור = ×1
      }
    }

    if (score > 0) scores[category] = score;
  }

  // סף ניקוד מינימלי: 15 נקודות = לפחות התאמה אחת של ביטוי 2 מילים בכותרת
  // ביטוי מילה אחת בכותרת = 5 נקודות (לא מספיק)
  // ביטוי 2 מילים בכותרת = 4×5 = 20 נקודות (מספיק)
  const MIN_SCORE = 15;

  if (Object.keys(scores).length === 0) {
    Logger.log(`No match for: "${titleLower.substring(0, 60)}" → שונות`);
    return 'שונות';
  }

  const best = Object.keys(scores).reduce((a, b) => scores[a] >= scores[b] ? a : b);
  if (scores[best] < MIN_SCORE) {
    Logger.log(`Weak match (${scores[best]} pts) for: "${titleLower.substring(0, 50)}" → שונות`);
    return 'שונות';
  }

  Logger.log(`Categorized: "${titleLower.substring(0, 50)}..." → ${best} (score: ${scores[best]})`);
  return best;
}


// ============================================================
// onOpen — תפריטים
// ============================================================

function onOpen() {
  const ui = SpreadsheetApp.getUi();

  ui.createMenu('📲 WhatsApp')
    .addItem('🔥 שלח מוצר יומי לוואטסאפ', 'sendWhatsAppProduct')
    .addToUi();

  ui.createMenu('🔗 קיצור לינקים')
    .addItem('✨ קצר את כל הלינקים', 'shortenAllLinks')
    .addItem('🔄 קצר לינקים ריקים בלבד', 'shortenEmptyLinks')
    .addSeparator()
    .addItem('🧪 בדיקה - קצר לינק אחד', 'testSingleLink')
    .addItem('ℹ️ הוראות', 'showInstructions')
    .addToUi();

  ui.createMenu('🏷️ קטגוריות')
    .addItem('🔄 מיין את כל המוצרים מחדש', 'recategorizeAll')
    .addItem('🧪 בדיקה - מיין שורה 2', 'testSingleCategorize')
    .addItem('📊 הצג סטטיסטיקה', 'showCategoryStats')
    .addToUi();
}


// ============================================================
// onEdit — טיפול אוטומטי בעריכות
// ============================================================

function onEdit(e) {
  if (!e || !e.source) return;

  const sheet = e.source.getActiveSheet();
  const range = e.range;
  const row = range.getRow();
  const col = range.getColumn();

  // עמודה A — URL מוצר → שלוף נתונים ומיין
  if (col === 1 && row > 1) {
    const productUrl = range.getValue();
    if (productUrl && productUrl.toString().includes('aliexpress.com')) {
      SpreadsheetApp.getActiveSpreadsheet().toast('מושך נתונים מ-AliExpress...', 'בתהליך', 3);
      fetchProductData(productUrl, row, sheet);
    }
  }

  // עמודה E — Affiliate Link → קצר אוטומטית
  if (col === 5 && row > 1) {
    const affiliateLink = range.getValue();
    if (affiliateLink && affiliateLink.toString().trim() !== '') {
      const existingShortLink = sheet.getRange(row, 8).getValue();
      if (!existingShortLink || existingShortLink.toString().trim() === '') {
        SpreadsheetApp.getActiveSpreadsheet().toast('מקצר לינק...', '⏳', 2);
        const shortLink = shortenWithIsGd(affiliateLink);
        if (shortLink) {
          sheet.getRange(row, 8).setValue(shortLink);
          SpreadsheetApp.getActiveSpreadsheet().toast('לינק קוצר!', '✅', 2);
        }
      }
    }
  }
}


// ============================================================
// שליפת נתוני מוצר מ-AliExpress
// ============================================================

function fetchProductData(url, row, sheet) {
  try {
    const apiUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`;
    const response = UrlFetchApp.fetch(apiUrl, { muteHttpExceptions: true });
    const html = response.getContentText();

    let title = '';
    const titleMatch = html.match(/<title>(.*?)<\/title>/i);
    if (titleMatch) title = titleMatch[1].replace(' - AliExpress', '').trim();

    let imageUrl = '';
    const imgMatch = html.match(/"imageUrl":"(.*?)"/);
    if (imgMatch) imageUrl = imgMatch[1].replace(/\\u002F/g, '/');

    let description = '';
    const descMatch = html.match(/<meta name="description" content="(.*?)"/i);
    if (descMatch) description = descMatch[1].substring(0, 200);

    const category = smartCategorize(title, description);

    if (title)       sheet.getRange(row, 2).setValue(title);
    if (description) sheet.getRange(row, 3).setValue(description);
    if (imageUrl)    sheet.getRange(row, 4).setValue(imageUrl);
    if (category)    sheet.getRange(row, 7).setValue(category);

    SpreadsheetApp.getActiveSpreadsheet().toast(`קטגוריה: ${category}`, '✅', 3);
  } catch (error) {
    SpreadsheetApp.getActiveSpreadsheet().toast('שגיאה: ' + error.toString(), 'שגיאה', 5);
    Logger.log('fetchProductData error: ' + error.toString());
  }
}

function fillAllProducts() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const lastRow = sheet.getLastRow();
  for (let row = 2; row <= lastRow; row++) {
    const url = sheet.getRange(row, 1).getValue();
    if (url && url.toString().includes('aliexpress.com')) {
      fetchProductData(url, row, sheet);
      Utilities.sleep(2000);
    }
  }
}


// ============================================================
// מיון קטגוריות — פונקציות עזר
// ============================================================

function recategorizeAll() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const ui = SpreadsheetApp.getUi();

  const response = ui.alert(
    '⚠️ אישור',
    'למיין את כל המוצרים מחדש?\n\nזה ידרוס את הקטגוריות הקיימות!',
    ui.ButtonSet.YES_NO
  );
  if (response !== ui.Button.YES) return;

  const data = sheet.getDataRange().getValues();
  let processed = 0, skipped = 0;

  SpreadsheetApp.getActiveSpreadsheet().toast('מתחיל מיון...', '⏳', 3);

  for (let i = 1; i < data.length; i++) {
    const title = data[i][1];       // Column B
    const description = data[i][2]; // Column C
    if (!title || title.toString().trim() === '') { skipped++; continue; }

    const category = smartCategorize(title, description);
    sheet.getRange(i + 1, 7).setValue(category);
    processed++;

    if (i % 10 === 0) {
      SpreadsheetApp.getActiveSpreadsheet().toast(`${i}/${data.length - 1}`, '⏳', 1);
    }
  }

  ui.alert('✅ הושלם!', `עובדו: ${processed}\nדולגו: ${skipped}\nסה"כ: ${data.length - 1}`, ui.ButtonSet.OK);
}

function testSingleCategorize() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const ui = SpreadsheetApp.getUi();
  const title = sheet.getRange(2, 2).getValue();
  const description = sheet.getRange(2, 3).getValue();
  if (!title) { ui.alert('❌', 'אין כותרת בשורה 2!', ui.ButtonSet.OK); return; }
  const category = smartCategorize(title, description);
  sheet.getRange(2, 7).setValue(category);
  ui.alert('✅', `המוצר סווג ל:\n"${category}"`, ui.ButtonSet.OK);
}

function showCategoryStats() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const ui = SpreadsheetApp.getUi();
  const data = sheet.getDataRange().getValues();
  const stats = {};
  for (let i = 1; i < data.length; i++) {
    const cat = data[i][6];
    if (cat && cat.toString().trim()) stats[cat] = (stats[cat] || 0) + 1;
  }
  let text = '📊 קטגוריות:\n\n';
  for (const [cat, count] of Object.entries(stats).sort((a, b) => b[1] - a[1])) {
    text += `${cat}: ${count}\n`;
  }
  ui.alert('📊 סטטיסטיקה', text, ui.ButtonSet.OK);
}


// ============================================================
// WhatsApp — שליחת מוצר יומי
// ============================================================

function sendWhatsAppProduct() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('❌', `לא נמצא גיליון "${SHEET_NAME}"`, SpreadsheetApp.getUi().ButtonSet.OK);
    return;
  }

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    SpreadsheetApp.getUi().alert('⚠️', 'אין מוצרים בטבלה!', SpreadsheetApp.getUi().ButtonSet.OK);
    return;
  }

  const data = sheet.getRange(2, 1, lastRow - 1, 9).getValues();
  const validRows = data.filter(row => row[COL.TITLE] && row[COL.TITLE].toString().trim() !== '');
  if (validRows.length === 0) {
    SpreadsheetApp.getUi().alert('⚠️', 'לא נמצאו מוצרים תקינים!', SpreadsheetApp.getUi().ButtonSet.OK);
    return;
  }

  const randomIndex = Math.floor(Math.random() * validRows.length);
  const product = validRows[randomIndex];

  const title       = (product[COL.TITLE] || '').toString().trim() || 'מוצר מומלץ';
  const description = (product[COL.DESCRIPTION] || '').toString().trim();
  const imageUrl    = (product[COL.IMAGE] || '').toString().trim();
  const shortLink   = (product[COL.SHORT_LINK] || '').toString().trim();
  const affLink     = (product[COL.AFFILIATE_LINK] || '').toString().trim();
  const category    = (product[COL.CATEGORY] || '').toString().trim();
  const finalLink   = shortLink || affLink || '';
  const priceRaw    = product[COL.PRICE];
  const price       = priceRaw && parseFloat(priceRaw) > 0
    ? `$${parseFloat(priceRaw).toFixed(2)}`
    : '';

  let shortDesc = description;
  if (shortDesc.length > 200) shortDesc = shortDesc.substring(0, 200) + '...';

  const message = buildWhatsAppMessage(title, shortDesc, finalLink, category, price);
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;

  showMessageDialog(title, message, whatsappUrl, imageUrl, randomIndex + 1, validRows.length, price);
}

function buildWhatsAppMessage(title, description, link, category, price) {
  const emojis = {
    'מוצרי חשמל': '🔌', 'מטבח ובית': '🍳', 'ספורט וכושר': '⚽',
    'תיקים ואביזרים': '👜', 'כלי עבודה': '🔧', 'צעצועים': '🎮',
    'אופנה': '👔', 'מוצרים לטלפון': '📱', 'שונות': '📦'
  };
  const emoji = emojis[category] || '🛍️';

  let msg = `🔥 *מוצר היום מ-M-SOLUTIONS!* 🔥\n\n`;
  msg += `📦 *${title}*\n\n`;
  if (price) msg += `💰 *מחיר: ${price}*\n\n`;
  if (description) msg += `${description}\n\n`;
  msg += `🛒 *להזמנה ישירות באלי אקספרס:*\n`;
  msg += link || '⚠️ אין קישור זמין';
  msg += `\n\n━━━━━━━━━━━━━━━━━━━━\n`;
  msg += `💎 משלוח מהיר | אחריות מלאה`;
  if (category) msg += `\n${emoji} קטגוריה: ${category}`;
  msg += `\n━━━━━━━━━━━━━━━━━━━━`;
  return msg;
}

function showMessageDialog(title, message, whatsappUrl, imageUrl, productNum, totalProducts, price) {
  const htmlContent = `
<!DOCTYPE html>
<html dir="rtl">
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 15px; background: #f0f2f5; direction: rtl; }
    .header { background: linear-gradient(135deg, #25D366, #128C7E); color: white; padding: 15px 20px; border-radius: 12px; margin-bottom: 15px; text-align: center; }
    .header h2 { margin: 0; font-size: 18px; }
    .header p { margin: 5px 0 0; font-size: 13px; opacity: 0.9; }
    .product-title { background: white; border-radius: 10px; padding: 12px 15px; margin-bottom: 12px; font-weight: bold; font-size: 14px; color: #1a202c; border-right: 4px solid #25D366; }
    .message-box { background: white; border-radius: 10px; padding: 12px; margin-bottom: 12px; }
    .message-box label { font-size: 12px; color: #666; font-weight: bold; display: block; margin-bottom: 6px; }
    textarea { width: 100%; height: 160px; border: 1px solid #ddd; border-radius: 8px; padding: 10px; font-family: inherit; font-size: 13px; resize: vertical; direction: rtl; box-sizing: border-box; }
    .buttons { display: flex; gap: 10px; flex-direction: column; }
    .btn { padding: 12px 20px; border: none; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; display: block; font-family: inherit; }
    .btn-whatsapp { background: #25D366; color: white; }
    .btn-whatsapp:hover { background: #20BA5A; }
    .btn-copy { background: #6c63ff; color: white; }
    .btn-copy:hover { background: #5a54d4; }
    .btn-new { background: #f0f2f5; color: #333; border: 1px solid #ddd; }
    .image-preview { background: white; border-radius: 10px; padding: 10px; margin-bottom: 12px; text-align: center; }
    .image-preview img { max-width: 100%; max-height: 150px; border-radius: 8px; object-fit: cover; }
    .image-preview a { font-size: 12px; color: #25D366; text-decoration: none; display: block; margin-top: 6px; }
    .counter { font-size: 11px; color: #999; text-align: center; margin-top: 10px; }
  </style>
</head>
<body>
  <div class="header">
    <h2>📲 הודעת WhatsApp מוכנה!</h2>
    <p>מוצר #${productNum} מתוך ${totalProducts}</p>
  </div>
  <div class="product-title">📦 ${title}${price ? ` — <span style="color:#25D366;font-weight:700">${price}</span>` : ''}</div>
  ${imageUrl ? `
  <div class="image-preview">
    <img src="${imageUrl}" alt="תמונה" onerror="this.style.display='none'">
    <a href="${imageUrl}" target="_blank">📷 פתח תמונה לשליחה ב-WhatsApp</a>
  </div>` : ''}
  <div class="message-box">
    <label>✉️ ההודעה (ניתן לערוך לפני שליחה):</label>
    <textarea id="msgArea">${message}</textarea>
  </div>
  <div class="buttons">
    <a href="${whatsappUrl}" target="_blank" class="btn btn-whatsapp">📲 פתח WhatsApp ושלח עכשיו</a>
    <button onclick="copyMessage()" class="btn btn-copy">📋 העתק הודעה ללוח</button>
    <button onclick="google.script.run.sendWhatsAppProduct(); google.script.host.close();" class="btn btn-new">🔀 בחר מוצר אחר</button>
  </div>
  <div class="counter">💡 לחץ "פתח WhatsApp" → בחר קבוצה → שלח!<br>יש תמונה? פתח אותה בנפרד ושלח יחד עם ההודעה</div>
  <script>
    function copyMessage() {
      const text = document.getElementById('msgArea').value;
      navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector('.btn-copy');
        btn.textContent = '✅ הועתק!';
        btn.style.background = '#28a745';
        setTimeout(() => { btn.textContent = '📋 העתק הודעה ללוח'; btn.style.background = '#6c63ff'; }, 2000);
      }).catch(() => { document.getElementById('msgArea').select(); document.execCommand('copy'); alert('✅ הועתק!'); });
    }
  </script>
</body>
</html>`;

  SpreadsheetApp.getUi().showModalDialog(
    HtmlService.createHtmlOutput(htmlContent).setWidth(400).setHeight(560),
    '📲 M-SOLUTIONS WhatsApp'
  );
}


// ============================================================
// קיצור לינקים עם is.gd
// ============================================================

function shortenAllLinks() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.alert('⚠️ אישור', 'לקצר את כל הלינקים?\nזה ידרוס לינקים קיימים!', ui.ButtonSet.YES_NO);
  if (response === ui.Button.YES) processLinks(false);
}

function shortenEmptyLinks() {
  processLinks(true);
}

function processLinks(skipExisting) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const ui = SpreadsheetApp.getUi();
  const data = sheet.getDataRange().getValues();
  const headers = data[0];

  const affiliateLinkCol = headers.indexOf('Affiliate Link');
  const shortLinkCol = headers.indexOf('Short Link');

  if (affiliateLinkCol === -1 || shortLinkCol === -1) {
    ui.alert('❌', 'חסרות עמודות!\nצריך: Affiliate Link + Short Link', ui.ButtonSet.OK);
    return;
  }

  SpreadsheetApp.getActiveSpreadsheet().toast('מתחיל...', '🚀', 3);
  let processed = 0, skipped = 0, failed = 0;

  for (let i = 1; i < data.length; i++) {
    const affiliateLink = data[i][affiliateLinkCol];
    const existingShortLink = data[i][shortLinkCol];
    if (!affiliateLink || affiliateLink.toString().trim() === '') { skipped++; continue; }
    if (skipExisting && existingShortLink && existingShortLink.toString().trim() !== '') { skipped++; continue; }

    SpreadsheetApp.getActiveSpreadsheet().toast(`${i}/${data.length - 1}`, '⏳', 2);
    const shortLink = shortenWithIsGd(affiliateLink);
    if (shortLink) {
      sheet.getRange(i + 1, shortLinkCol + 1).setValue(shortLink);
      processed++;
      Utilities.sleep(500);
    } else {
      failed++;
    }
  }

  ui.alert('✅ סיים!', `עובדו: ${processed}\nדולגו: ${skipped}\nנכשלו: ${failed}`, ui.ButtonSet.OK);
}

function testSingleLink() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const ui = SpreadsheetApp.getUi();
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const affiliateLinkCol = headers.indexOf('Affiliate Link');
  const shortLinkCol = headers.indexOf('Short Link');
  if (affiliateLinkCol === -1 || shortLinkCol === -1) {
    ui.alert('❌', 'לא נמצאו עמודות Affiliate Link / Short Link', ui.ButtonSet.OK); return;
  }
  const affiliateLink = sheet.getRange(2, affiliateLinkCol + 1).getValue();
  if (!affiliateLink) { ui.alert('❌', 'אין לינק בשורה 2!', ui.ButtonSet.OK); return; }
  SpreadsheetApp.getActiveSpreadsheet().toast('מקצר...', '⏳', 3);
  const shortLink = shortenWithIsGd(affiliateLink);
  if (shortLink) {
    sheet.getRange(2, shortLinkCol + 1).setValue(shortLink);
    ui.alert('✅ הצלחה!', `${shortLink}`, ui.ButtonSet.OK);
  } else {
    ui.alert('❌', 'לא הצלחתי לקצר.', ui.ButtonSet.OK);
  }
}

function shortenWithIsGd(longUrl) {
  try {
    const apiUrl = 'https://is.gd/create.php?format=simple&url=' + encodeURIComponent(longUrl);
    const response = UrlFetchApp.fetch(apiUrl, { muteHttpExceptions: true, followRedirects: false });
    if (response.getResponseCode() === 200) {
      const shortUrl = response.getContentText().trim();
      if (shortUrl.startsWith('https://is.gd/') && shortUrl.length < 30) return shortUrl;
    }
    return null;
  } catch (error) {
    Logger.log('shortenWithIsGd error: ' + error.toString());
    return null;
  }
}

function showInstructions() {
  SpreadsheetApp.getUi().alert('📖 הוראות', `
קיצור לינקים עם is.gd:

1️⃣  בדיקה: תפריט "קיצור לינקים" → בדיקה
2️⃣  קצר הכל: תפריט → "קצר לינקים ריקים בלבד"

המערכת קוראת מעמודה E (Affiliate Link)
ושומרת בעמודה H (Short Link)

WhatsApp:
לחץ על כפתור "📲 WhatsApp יומי" לשליחת מוצר רנדומלי
  `, SpreadsheetApp.getUi().ButtonSet.OK);
}
