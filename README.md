# Insta AI Studio

**Instagram Reels uchun AI asosidagi kontent yaratish va boshqarish platformasi.**

Insta AI Studio — kontent yaratuvchilar va Instagram sahifa egalari uchun ishlab chiqilayotgan web-platforma. Loyiha sun’iy intellekt imkoniyatlari orqali video kontent bilan ishlash, Instagram hisobini boshqarish va statistik ma’lumotlarni kuzatishni bir joyga jamlashga qaratilgan.

---

## ✨ Imkoniyatlar

- 🤖 **AI integratsiyasi** — Google Gemini orqali sun’iy intellekt funksiyalari.
- 🎬 **Video bilan ishlash** — Reels videolarini yuklash va tahlil qilish.
- 📱 **Instagram integratsiyasi** — Meta Instagram API orqali hisob bilan ishlash.
- 📊 **Analytics** — Instagram faoliyati va statistik ma’lumotlarini kuzatish.
- 🗂️ **History** — oldingi ishlar va faoliyat tarixini ko‘rish.
- 👤 **Profile** — Instagram profiliga oid ma’lumotlar.
- 🔐 **Authentication** — boshqaruv paneliga parol orqali kirish.
- 📱 **Responsive UI** — kompyuter va mobil qurilmalarga mos interfeys.

## 🛠 Texnologiyalar

| Qism | Texnologiya |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| AI | Google Gemini API |
| Instagram | Meta Instagram API |
| Server | Uvicorn |
| Deployment | Render |

## 📁 Loyiha tuzilishi

```text
insta-ai-studio/
│
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── gemini_ai.py
│   ├── instagram_api.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── analytics.html
│   ├── history.html
│   ├── profile.html
│   ├── reels.html
│   ├── api-config.js
│   ├── login.js
│   └── static/
│
├── .gitignore
├── render.yaml
└── README.md
```

## ⚙️ O‘rnatish

### 1. Repository'ni yuklab olish

```bash
git clone https://github.com/khayitboyeff/Instagram.ai.git
cd Instagram.ai
```


### 2. Virtual environment yaratish

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Kutubxonalarni o‘rnatish

```powershell
pip install -r backend/requirements.txt
```

### 4. Muhit sozlamalari

`backend/.env.example` faylidan nusxa olib, `backend/.env` yarating.

Quyidagi qiymatlarni o‘z API ma’lumotlaringiz bilan to‘ldiring:

```env
APP_NAME=Insta AI Studio
HOST=127.0.0.1
PORT=8001

SESSION_SECRET=your_random_secret
DASHBOARD_PASSWORD=your_secure_password

FRONTEND_URL=http://localhost:8888
APP_BASE_URL=http://127.0.0.1:8001

IG_ACCESS_TOKEN=your_instagram_access_token
IG_USER_ID=your_instagram_user_id
IG_USERNAME=your_instagram_username

GEMINI_API_KEY=your_gemini_api_key
```

**Muhim:** Haqiqiy API kalitlari va maxfiy ma’lumotlarni GitHub repository'ga yuklamang.

### 5. Backend'ni ishga tushirish

```powershell
cd backend
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8001
```

API hujjatlari:

```text
http://127.0.0.1:8001/docs
```

Frontend'ni `http://localhost:8888` manzilida xizmat qiladigan lokal HTTP server orqali oching. `frontend/api-config.js` dagi API manzili backend manziliga mos bo‘lishi kerak.

## 🔑 Kerakli API xizmatlari

Loyihaning integratsiya imkoniyatlaridan foydalanish uchun:

- Google Gemini API — https://ai.google.dev/
- Meta for Developers — https://developers.facebook.com/

Instagram integratsiyasi uchun tegishli Meta ruxsatlari, hisob sozlamalari va access token talab qilinadi.

## 🚀 Deployment

Loyihani GitHub orqali Render platformasiga joylashtirish rejalashtirilgan.

`render.yaml` fayli backend API va frontend Static Site xizmatlarini sozlash uchun ishlatiladi.

Deployment paytida quyidagi environment variable'lar Render boshqaruv panelida sozlanishi kerak:

- `SESSION_SECRET`
- `DASHBOARD_PASSWORD`
- `APP_BASE_URL`
- `FRONTEND_URL`
- `IG_ACCESS_TOKEN`
- `IG_USER_ID`
- `IG_USERNAME`
- `GEMINI_API_KEY`

**Eslatma:** Bepul hostingda doimiy fayl saqlash va ma’lumotlar bazasi uchun alohida yechim talab qilinishi mumkin.

## 🔒 Xavfsizlik

- API kalitlarini frontend kodiga joylashtirmang.
- `.env` fayllarini GitHub'ga yuklamang.
- Instagram hisobiga faqat kerakli ruxsatlar bilan ulaning.
- Foydalanuvchi ma’lumotlarini himoya qiling.
- Production muhitida kuchli maxfiy parollardan foydalaning.

## 🎯 Loyiha maqsadi

Insta AI Studio'ning maqsadi — Instagram kontent yaratuvchilari uchun AI, video bilan ishlash va hisob boshqaruvi vositalarini yagona platformada birlashtirish.

## 📌 Loyiha holati

**Development / MVP**

Loyiha faol ishlab chiqilmoqda. Yangi imkoniyatlar, optimallashtirish va integratsiyalar bosqichma-bosqich qo‘shiladi.

---

**Insta AI Studio**  
*Create smarter. Manage better. Grow with AI.*
