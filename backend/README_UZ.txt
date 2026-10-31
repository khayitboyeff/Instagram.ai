INSTA AI STUDIO v1.1.0 — BACKEND

Deploy: Render -> New Web Service -> backend papkasini root directory qilib tanlang. render.yaml ham mavjud.
Build: pip install -r requirements.txt
Start: uvicorn app:app --host 0.0.0.0 --port $PORT

Render Environment: APP_BASE_URL = Render backend URL; FRONTEND_URL = Netlify frontend URL; DASHBOARD_PASSWORD; SESSION_SECRET; IG_ACCESS_TOKEN; IG_USER_ID; GEMINI_API_KEY.

MUHIM: render.yaml persistent disk qo‘shadi. Persistent disk Render pullik rejalarida mavjud. Bepul rejada SQLite va yuklangan videolar doimiy saqlanmasligi mumkin.
APP_BASE_URL Instagram Meta video faylini yuklab olishi uchun backendning public HTTPS URL bo‘lishi kerak.
