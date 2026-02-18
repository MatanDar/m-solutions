/**
 * ============================================================
 * M-SOLUTIONS WhatsApp Button - Google Apps Script
 * ============================================================
 *
 * HOW TO ADD THIS BUTTON TO YOUR GOOGLE SHEET:
 * ──────────────────────────────────────────────────────────
 * 1. פתח את גיליון ה-Google Sheets שלך
 * 2. לחץ על "Extensions" (תוספות) → "Apps Script"
 * 3. מחק את כל הקוד הקיים ו-הדבק את כל הקוד הזה
 * 4. שמור (Ctrl+S)
 * 5. חזור לגיליון
 * 6. לחץ על "Insert" (הוספה) → "Drawing" (ציור)
 * 7. צייר כפתור (Rectangle) → כתוב עליו "📲 WhatsApp יומי"
 * 8. לחץ על נקודות (...) → "Assign script"
 * 9. כתוב: sendWhatsAppProduct → לחץ OK
 * ──────────────────────────────────────────────────────────
 *
 * הכפתור יבחר מוצר רנדומלי מהטבלה ויפתח הודעת WhatsApp מוכנה!
 */


// ===== הגדרות =====
const SHEET_NAME = 'Affiliate Table';

// עמודות לפי סדר: A=URL, B=Title, C=Description, D=Image, E=AffiliateLink, F=LastUpdated, G=Category, H=ShortLink
const COL = {
  URL: 0,
  TITLE: 1,
  DESCRIPTION: 2,
  IMAGE: 3,
  AFFILIATE_LINK: 4,
  LAST_UPDATED: 5,
  CATEGORY: 6,
  SHORT_LINK: 7
};


/**
 * פונקציה ראשית - שולחת הודעת WhatsApp עם מוצר רנדומלי
 * מחוברת לכפתור בגיליון
 */
function sendWhatsAppProduct() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);

  if (!sheet) {
    SpreadsheetApp.getUi().alert('❌ שגיאה', `לא נמצא גיליון בשם "${SHEET_NAME}"`, SpreadsheetApp.getUi().ButtonSet.OK);
    return;
  }

  // קבלת כל השורות (ללא שורת הכותרת)
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    SpreadsheetApp.getUi().alert('⚠️', 'אין מוצרים בטבלה!', SpreadsheetApp.getUi().ButtonSet.OK);
    return;
  }

  const data = sheet.getRange(2, 1, lastRow - 1, 8).getValues();

  // סינון שורות ריקות
  const validRows = data.filter(row => row[COL.TITLE] && row[COL.TITLE].toString().trim() !== '');

  if (validRows.length === 0) {
    SpreadsheetApp.getUi().alert('⚠️', 'לא נמצאו מוצרים תקינים בטבלה!', SpreadsheetApp.getUi().ButtonSet.OK);
    return;
  }

  // בחירת מוצר רנדומלי
  const randomIndex = Math.floor(Math.random() * validRows.length);
  const product = validRows[randomIndex];

  // חילוץ נתוני המוצר
  const title = product[COL.TITLE] ? product[COL.TITLE].toString().trim() : 'מוצר מומלץ';
  const description = product[COL.DESCRIPTION] ? product[COL.DESCRIPTION].toString().trim() : '';
  const imageUrl = product[COL.IMAGE] ? product[COL.IMAGE].toString().trim() : '';
  const shortLink = product[COL.SHORT_LINK] ? product[COL.SHORT_LINK].toString().trim() : '';
  const affiliateLink = product[COL.AFFILIATE_LINK] ? product[COL.AFFILIATE_LINK].toString().trim() : '';
  const category = product[COL.CATEGORY] ? product[COL.CATEGORY].toString().trim() : '';

  // קישור - עדיפות ל-Short Link, אחרת Affiliate Link
  const finalLink = shortLink || affiliateLink || '';

  // קיצור תיאור ל-200 תווים
  let shortDesc = description;
  if (shortDesc.length > 200) {
    shortDesc = shortDesc.substring(0, 200) + '...';
  }

  // בניית הודעת WhatsApp
  const message = buildWhatsAppMessage(title, shortDesc, finalLink, category);

  // קידוד ה-URL לפתיחת WhatsApp
  const encodedMessage = encodeURIComponent(message);
  const whatsappUrl = `https://wa.me/?text=${encodedMessage}`;

  // הצגת דיאלוג עם ההודעה ולינק לשליחה
  showMessageDialog(title, message, whatsappUrl, imageUrl, randomIndex + 1, validRows.length);
}


/**
 * בניית הודעת WhatsApp
 */
function buildWhatsAppMessage(title, description, link, category) {
  const categoryEmoji = getCategoryEmoji(category);

  let message = `🔥 *מוצר היום מ-M-SOLUTIONS!* 🔥\n\n`;
  message += `📦 *${title}*\n\n`;

  if (description) {
    message += `${description}\n\n`;
  }

  message += `🛒 *להזמנה ישירות באלי אקספרס:*\n`;
  message += link ? link : '⚠️ אין קישור זמין';
  message += `\n\n━━━━━━━━━━━━━━━━━━━━\n`;
  message += `💎 משלוח מהיר | אחריות מלאה`;

  if (category) {
    message += `\n${categoryEmoji} קטגוריה: ${category}`;
  }

  message += `\n━━━━━━━━━━━━━━━━━━━━`;

  return message;
}


/**
 * אמוג'י לפי קטגוריה
 */
function getCategoryEmoji(category) {
  const emojis = {
    'מוצרי חשמל': '🔌',
    'מטבח ובית': '🍳',
    'ספורט וכושר': '⚽',
    'תיקים ואביזרים': '👜',
    'כלי עבודה': '🔧',
    'צעצועים': '🎮',
    'אופנה': '👔',
    'מוצרים לטלפון': '📱'
  };
  return emojis[category] || '🛍️';
}


/**
 * הצגת דיאלוג עם ההודעה
 */
function showMessageDialog(title, message, whatsappUrl, imageUrl, productNum, totalProducts) {
  const htmlContent = `
<!DOCTYPE html>
<html dir="rtl">
<head>
  <meta charset="UTF-8">
  <style>
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      margin: 0;
      padding: 15px;
      background: #f0f2f5;
      direction: rtl;
    }
    .header {
      background: linear-gradient(135deg, #25D366, #128C7E);
      color: white;
      padding: 15px 20px;
      border-radius: 12px;
      margin-bottom: 15px;
      text-align: center;
    }
    .header h2 { margin: 0; font-size: 18px; }
    .header p { margin: 5px 0 0; font-size: 13px; opacity: 0.9; }
    .product-title {
      background: white;
      border-radius: 10px;
      padding: 12px 15px;
      margin-bottom: 12px;
      font-weight: bold;
      font-size: 14px;
      color: #1a202c;
      border-right: 4px solid #25D366;
    }
    .message-box {
      background: white;
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 12px;
    }
    .message-box label {
      font-size: 12px;
      color: #666;
      font-weight: bold;
      display: block;
      margin-bottom: 6px;
    }
    textarea {
      width: 100%;
      height: 160px;
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 10px;
      font-family: inherit;
      font-size: 13px;
      resize: vertical;
      direction: rtl;
      box-sizing: border-box;
    }
    .buttons {
      display: flex;
      gap: 10px;
      flex-direction: column;
    }
    .btn {
      padding: 12px 20px;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: bold;
      cursor: pointer;
      text-decoration: none;
      text-align: center;
      display: block;
      font-family: inherit;
    }
    .btn-whatsapp {
      background: #25D366;
      color: white;
    }
    .btn-whatsapp:hover { background: #20BA5A; }
    .btn-copy {
      background: #6c63ff;
      color: white;
    }
    .btn-copy:hover { background: #5a54d4; }
    .btn-new {
      background: #f0f2f5;
      color: #333;
      border: 1px solid #ddd;
    }
    .image-preview {
      background: white;
      border-radius: 10px;
      padding: 10px;
      margin-bottom: 12px;
      text-align: center;
    }
    .image-preview img {
      max-width: 100%;
      max-height: 150px;
      border-radius: 8px;
      object-fit: cover;
    }
    .image-preview a {
      font-size: 12px;
      color: #25D366;
      text-decoration: none;
      display: block;
      margin-top: 6px;
    }
    .counter {
      font-size: 11px;
      color: #999;
      text-align: center;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h2>📲 הודעת WhatsApp מוכנה!</h2>
    <p>מוצר #${productNum} מתוך ${totalProducts}</p>
  </div>

  <div class="product-title">📦 ${title}</div>

  ${imageUrl ? `
  <div class="image-preview">
    <img src="${imageUrl}" alt="תמונת המוצר" onerror="this.style.display='none'">
    <a href="${imageUrl}" target="_blank">📷 פתח תמונה בחלון חדש (לשליחה ב-WhatsApp)</a>
  </div>
  ` : ''}

  <div class="message-box">
    <label>✉️ ההודעה (אפשר לערוך לפני שליחה):</label>
    <textarea id="msgArea">${message}</textarea>
  </div>

  <div class="buttons">
    <a href="${whatsappUrl}" target="_blank" class="btn btn-whatsapp">
      📲 פתח WhatsApp ושלח עכשיו
    </a>
    <button onclick="copyMessage()" class="btn btn-copy">
      📋 העתק הודעה ללוח
    </button>
    <button onclick="google.script.run.sendWhatsAppProduct(); google.script.host.close();" class="btn btn-new">
      🔀 בחר מוצר אחר
    </button>
  </div>

  <div class="counter">
    💡 לחץ על "פתח WhatsApp" → בחר קבוצה → שלח!<br>
    אם יש תמונה - פתח אותה בנפרד ושלח יחד עם ההודעה
  </div>

  <script>
    function copyMessage() {
      const text = document.getElementById('msgArea').value;
      navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector('.btn-copy');
        btn.textContent = '✅ הועתק!';
        btn.style.background = '#28a745';
        setTimeout(() => {
          btn.textContent = '📋 העתק הודעה ללוח';
          btn.style.background = '#6c63ff';
        }, 2000);
      }).catch(() => {
        // Fallback
        document.getElementById('msgArea').select();
        document.execCommand('copy');
        alert('✅ הועתק!');
      });
    }
  </script>
</body>
</html>
`;

  const html = HtmlService.createHtmlOutput(htmlContent)
    .setWidth(400)
    .setHeight(560);

  SpreadsheetApp.getUi().showModalDialog(html, '📲 M-SOLUTIONS WhatsApp');
}


/**
 * יוצר תפריט בגיליון
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📲 M-SOLUTIONS')
    .addItem('שלח מוצר יומי ל-WhatsApp', 'sendWhatsAppProduct')
    .addItem('בחר מוצר רנדומלי', 'sendWhatsAppProduct')
    .addToUi();
}
