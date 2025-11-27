# 🎬 YouTube Automation - M-Solutions

מערכת אוטומטית שיוצרת סרטונים מתמונות של מוצרי AliExpress ומעלה אותם ליוטיוב!

---

## ✨ מה המערכת עושה:

1. 🎯 **בוחרת מוצר אקראי** מ-Google Sheets
2. 📥 **מורידה את התמונה** של המוצר
3. 🎬 **יוצרת סרטון 15 שניות** עם:
   - אנימציות (Zoom In/Out)
   - טקסט בעברית
   - הלוגו שלך
   - מוזיקת רקע
4. 📺 **מעלה ליוטיוב** אוטומטית
5. ⏰ **3 פעמים ביום**: 09:00, 14:00, 19:00

---

## 🔧 הגדרת YouTube API

### שלב 1: יצירת פרויקט ב-Google Cloud

1. לך ל: https://console.cloud.google.com
2. לחץ **"Create Project"**
3. שם הפרויקט: `M-Solutions-YouTube`
4. לחץ **"Create"**

### שלב 2: הפעלת YouTube Data API

1. לך ל: https://console.cloud.google.com/apis/library
2. חפש: `YouTube Data API v3`
3. לחץ **"Enable"**

### שלב 3: יצירת Service Account

1. לך ל: https://console.cloud.google.com/iam-admin/serviceaccounts
2. לחץ **"Create Service Account"**
3. שם: `youtube-uploader`
4. תפקיד: `Editor`
5. לחץ **"Done"**

### שלב 4: יצירת מפתח (Key)

1. לחץ על ה-Service Account שיצרת
2. לחץ **"Keys"** → **"Add Key"** → **"Create new key"**
3. בחר **JSON**
4. הקובץ ירד למחשב שלך

### שלב 5: הוספת Service Account לערוץ YouTube

⚠️ **חשוב מאוד!**

1. לך לערוץ YouTube שלך: https://studio.youtube.com
2. **Settings** → **Permissions**
3. לחץ **"Invite"**
4. הוסף את האימייל של ה-Service Account (נראה כך: `youtube-uploader@...iam.gserviceaccount.com`)
5. תן הרשאות: **Manager**
6. לחץ **"Save"**

---

## 🔐 הוספת Secrets ל-GitHub

### Secret חדש: `YOUTUBE_CREDENTIALS`

1. לך ל: https://github.com/MatanDar/m-solutions/settings/secrets/actions
2. לחץ **"New repository secret"**
3. שם: `YOUTUBE_CREDENTIALS`
4. ערך: **העתק את כל התוכן מקובץ ה-JSON שהורדת**
5. לחץ **"Add secret"**

---

## 📂 מבנה הקבצים:

```
m-solutions/
├── .github/workflows/
│   ├── update_products.yml          # עדכון מוצרים מAliExpress
│   └── upload_youtube_videos.yml    # ✨ חדש! העלאת סרטונים
├── update_aliexpress_to_sheets.py
├── create_video_and_upload.py       # ✨ חדש!
├── logo.png                         # ✨ חדש!
├── requirements.txt
└── index.html
```

---

## 🚀 הרצה ידנית:

1. לך ל: https://github.com/MatanDar/m-solutions/actions
2. לחץ על **"Upload YouTube Videos Daily"**
3. לחץ **"Run workflow"** → **"Run workflow"**

---

## 🎬 מבנה הסרטון:

```
⏱️ 0-3 שניות:   תמונת המוצר + Zoom In
📝 3-6 שניות:   "😍 [שם המוצר]"
⭐ 6-9 שניות:   "⭐ דירוג: X.X"
🔥 9-12 שניות:  "🔥 מוצר חם!"
👇 12-15 שניות: "👇 לחצו על הלינק!"
🎵 כל הזמן:     מוזיקת רקע + הלוגו בפינה
```

---

## 📊 סטטיסטיקה:

```
📺 סרטונים: 3 ביום = 90 בחודש
⏰ שעות: 09:00, 14:00, 19:00
🎬 אורך: 15 שניות
💰 עלות: 0 ש"ח (חינמי לגמרי!)
```

---

## ❓ בעיות נפוצות:

### שגיאה: "Quota exceeded"
- YouTube מגביל ל-6 העלאות ביום לחשבונות חדשים
- פתרון: המתן 24 שעות

### שגיאה: "Forbidden"
- ה-Service Account לא הוסף לערוץ YouTube
- פתרון: עקוב אחר "שלב 5" למעלה

---

## 🎉 סיכום:

המערכת **עובדת 24/7 בלי שהמחשב שלך דולק!**

✅ חינמי לגמרי
✅ אוטומטי לגמרי
✅ 3 סרטונים ביום
✅ כפתור להרצה ידנית

**עבודה מצוינת מתן!** 🚀