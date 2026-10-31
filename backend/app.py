import asyncio
import secrets
import shutil
import subprocess
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi.staticfiles import StaticFiles
import config
import database as db
from instagram_api import (
    get_profile,
    get_recent_media,
    get_media_insights,
    get_account_insights,
    publish_reel,
    InstagramAPIError,
)
from gemini_ai import analyze_video, generate_cover_from_uri, GeminiError


# =========================================================
# APP CONFIGURATION
# =========================================================

app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
)

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

_token_serializer = URLSafeTimedSerializer(
    config.SESSION_SECRET or "change-this-session-secret",
    salt="insta-ai-api",
)


# =========================================================
# AUTHENTICATION
# =========================================================

def _token_ok(request: Request) -> bool:
    header = request.headers.get("Authorization", "")

    if not header.startswith("Bearer "):
        return False

    try:
        data = _token_serializer.loads(
            header[7:],
            max_age=config.ACCESS_TOKEN_TTL_HOURS * 3600,
        )
        return data.get("authenticated") is True

    except (BadSignature, SignatureExpired):
        return False


@app.on_event("startup")
def startup():
    db.init_db()


# =========================================================
# API AUTH MIDDLEWARE
# =========================================================

@app.middleware("http")
async def protect_api(request: Request, call_next):

    # CORS OPTIONS so'rovlarini autentifikatsiyasiz o'tkazamiz.
    # Bu dashboard loginidan keyingi 401 xatosini bartaraf etadi.
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path

    # Ochiq API manzillari
    public = (
        path in {
            "/api/health",
            "/api/auth/login",
        }
        or path.startswith("/media/public/")
        or path.startswith("/api/cover/")
    )

    # Faqat himoyalangan API so'rovlarini tekshiramiz
    if path.startswith("/api/") and not public:

        if not _token_ok(request):
            return JSONResponse(
                {
                    "ok": False,
                    "error": "Sessiya tugagan. Qayta kiring.",
                },
                status_code=401,
            )

    return await call_next(request)


# =========================================================
# INSTAGRAM CONNECTION
# =========================================================

def instagram_connection():
    """
    Instagram ma'lumotlarini faqat .env faylidan oladi.
    """

    if not config.IG_ACCESS_TOKEN:
        return None

    return {
        "token": config.IG_ACCESS_TOKEN,
        "user_id": config.IG_USER_ID,
        "username": config.IG_USERNAME,
        "expires_at": "",
    }


def require_https_base() -> None:
    parsed = urlparse(config.APP_BASE_URL)

    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(
            400,
            "Instagram Reels joylash uchun APP_BASE_URL backendning ommaviy HTTPS manzili bo‘lishi kerak.",
        )


# =========================================================
# AUTH API
# =========================================================

@app.post("/api/auth/login")
async def api_login(request: Request):

    data = await request.json()
    password = str(data.get("password", ""))

    if not config.DASHBOARD_PASSWORD or not config.SESSION_SECRET:
        raise HTTPException(
            500,
            "Backend Environment ichida DASHBOARD_PASSWORD va SESSION_SECRET sozlang.",
        )

    if not secrets.compare_digest(
        password,
        config.DASHBOARD_PASSWORD,
    ):
        db.add_history(
            "Kirish urinishi",
            "Noto‘g‘ri parol",
            "failed",
        )

        raise HTTPException(
            401,
            "Parol noto‘g‘ri.",
        )

    token = _token_serializer.dumps(
        {"authenticated": True}
    )

    db.add_history(
        "Tizimga kirish",
        "Shaxsiy dashboard ochildi",
    )

    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "expires_in": config.ACCESS_TOKEN_TTL_HOURS * 3600,
    }


@app.get("/api/auth/me")
async def api_auth_me():

    return {
        "ok": True,
        "authenticated": True,
    }


@app.post("/api/auth/logout")
async def api_logout():

    return {
        "ok": True,
    }


# =========================================================
# INSTAGRAM PROFILE
# =========================================================

@app.get("/api/profile")
async def api_profile():

    connection = instagram_connection()

    if not connection:
        return {
            "connected": False,
            "message": ".env faylida IG_ACCESS_TOKEN va IG_USER_ID qiymatlarini kiriting.",
        }

    try:
        profile = get_profile(connection["token"])

        profile["connected"] = True
        profile["expires_at"] = connection.get("expires_at", "")

        if not connection.get("user_id"):
            connection["user_id"] = str(
                profile.get("user_id") or ""
            )

        return profile

    except (
        InstagramAPIError,
        requests.RequestException,
    ) as exc:

        raise HTTPException(
            502,
            f"Instagram profilini olishda xato: {exc}",
        )


@app.post("/api/profile/draft")
async def save_profile_draft(request: Request):

    data = await request.json()

    username = (
        str(data.get("username", ""))
        .strip()
        .lstrip("@")[:30]
    )

    biography = (
        str(data.get("biography", ""))
        .strip()[:150]
    )

    if not username and not biography:
        raise HTTPException(
            400,
            "Username yoki bio matnidan kamida bittasini kiriting.",
        )

    details = (
        f"Yangi username: @{username or 'o‘zgarmaydi'} "
        f"| Yangi bio: {biography or 'o‘zgarmaydi'}"
    )

    db.add_history(
        "Profil o‘zgarishi tayyorlandi",
        details,
    )

    return {
        "ok": True,
        "message": "Matnlar tarixga saqlandi. Instagram profilini tahrirlash sahifasida o‘zgarishni o‘zingiz tasdiqlang.",
    }


# =========================================================
# INSTAGRAM ANALYTICS
# =========================================================

@app.get("/api/analytics")
async def api_analytics():

    connection = instagram_connection()

    if not connection:
        raise HTTPException(
            400,
            ".env faylida IG_ACCESS_TOKEN qiymati sozlanmagan.",
        )

    token = connection["token"]

    try:
        profile = get_profile(token)
        account_insights = get_account_insights(token)
        media = get_recent_media(token, 30)

        reels = [
            item
            for item in media
            if (
                item.get("media_product_type") == "REELS"
                or item.get("media_type") == "VIDEO"
            )
        ]

        results = []

        for item in reels[:12]:

            insights = get_media_insights(
                token,
                str(item.get("id", "")),
            )

            results.append(
                {
                    "id": item.get("id"),
                    "caption": item.get("caption", ""),
                    "timestamp": item.get("timestamp", ""),
                    "permalink": item.get("permalink", ""),
                    "thumbnail_url": (
                        item.get("thumbnail_url")
                        or item.get("media_url", "")
                    ),
                    "like_count": item.get(
                        "like_count",
                        insights.get("likes", 0),
                    ),
                    "comments_count": item.get(
                        "comments_count",
                        insights.get("comments", 0),
                    ),
                    "insights": insights,
                }
            )

        db.add_history(
            "Instagram statistikasi yangilandi",
            f"{len(results)} ta Reels ma’lumoti",
        )

        return {
            "profile": profile,
            "account_insights": account_insights,
            "reels": results,
        }

    except (
        InstagramAPIError,
        requests.RequestException,
    ) as exc:

        db.add_history(
            "Statistikani olish",
            str(exc),
            "failed",
        )

        raise HTTPException(
            502,
            f"Instagram statistikasi olinmadi: {exc}",
        )


# =========================================================
# REELS VIDEO PREPARATION
# =========================================================

@app.post("/api/reels/prepare")
async def prepare_reel(
    video: UploadFile = File(...),
    use_ai: bool = Form(True),
):

    filename = Path(
        video.filename or "video.mp4"
    ).name

    suffix = Path(filename).suffix.lower()

    if suffix not in {".mp4", ".mov"}:
        raise HTTPException(
            400,
            "Faqat MP4 yoki MOV video fayl yuboring.",
        )

    draft_id = uuid.uuid4().hex

    stored_path = (
        config.UPLOAD_DIR / f"{draft_id}{suffix}"
    )

    total = 0

    try:
        with stored_path.open("wb") as out:

            while chunk := await video.read(1024 * 1024):

                total += len(chunk)

                if total > config.MAX_UPLOAD_MB * 1024 * 1024:

                    out.close()
                    stored_path.unlink(missing_ok=True)

                    raise HTTPException(
                        413,
                        f"Video {config.MAX_UPLOAD_MB} MB limitdan katta.",
                    )

                out.write(chunk)

    finally:
        await video.close()

    if total == 0:

        stored_path.unlink(missing_ok=True)

        raise HTTPException(
            400,
            "Video fayl bo‘sh.",
        )

    public_token = secrets.token_urlsafe(36)

    cover_filename = ""
    caption = ""
    hashtags = ""
    summary = ""
    content_prompt = ""
    gemini_file_uri = ""
    gemini_file_mime_type = ""
    status = "draft"

    if use_ai:

        try:
            # Gemini SDK ishini FastAPI event loopidan tashqarida bajaramiz.
            ai_result = await asyncio.to_thread(
                analyze_video,
                stored_path,
            )

            caption = str(
                ai_result.get("caption", "")
            )[:2200]

            hashtags_value = ai_result.get(
                "hashtags",
                [],
            )

            hashtags = (
                " ".join(hashtags_value)
                if isinstance(hashtags_value, list)
                else str(hashtags_value)
            )

            summary = str(
                ai_result.get("video_summary", "")
            )[:1000]

            content_prompt = str(
                ai_result.get("content_prompt", "")
            )[:4000]

            gemini_file_uri = str(
                ai_result.get("gemini_file_uri", "")
            )

            gemini_file_mime_type = str(
                ai_result.get("gemini_file_mime_type", "")
            )

            db.add_history(
                "Gemini video tahlili",
                f"{filename}; matnli AI natijasi tayyor",
            )

        except GeminiError as exc:

            db.add_history(
                "Gemini video tahlili",
                str(exc),
                "failed",
            )

            summary = f"AI xatosi: {exc}"

    db.create_draft(
        {
            "id": draft_id,
            "filename": filename,
            "stored_path": str(stored_path),
            "public_token": public_token,
            "caption": caption,
            "hashtags": hashtags,
            "video_summary": summary,
            "content_prompt": content_prompt,
            "gemini_file_uri": gemini_file_uri,
            "gemini_file_mime_type": gemini_file_mime_type,
            "cover_filename": cover_filename,
            "status": status,
        }
    )

    db.add_history(
        "Reels video yuklandi",
        f"{filename} ({round(total / 1024 / 1024, 2)} MB)",
    )

    return {
        "ok": True,
        "draft_id": draft_id,
        "filename": filename,
        "caption": caption,
        "hashtags": hashtags,
        "video_summary": summary,
        "content_prompt": content_prompt,
        "cover_url": "",
        "cover_ready": False,
        "ai_enabled": use_ai,
        "gemini_ready": bool(gemini_file_uri),
        "size_mb": round(total / 1024 / 1024, 2),
    }


# =========================================================
# REELS COVER GENERATION
# =========================================================

@app.post("/api/reels/{draft_id}/cover")
async def create_reel_cover(draft_id: str):

    draft = db.get_draft(draft_id)

    if not draft:
        raise HTTPException(
            404,
            "Reels draft topilmadi.",
        )

    stored_path = Path(
        draft.get("stored_path", "")
    )

    if not stored_path.is_file():
        raise HTTPException(
            404,
            "Yuklangan video fayli topilmadi.",
        )

    video_uri = str(
        draft.get("gemini_file_uri", "")
    )

    mime_type = str(
        draft.get("gemini_file_mime_type", "video/mp4")
    )

    try:

        # Eski yoki muddati o'tgan Gemini fayl manzilini yangilaymiz.
        if not video_uri:

            from gemini_ai import upload_video_reference

            refreshed = await asyncio.to_thread(
                upload_video_reference,
                stored_path,
            )

            video_uri = refreshed["uri"]
            mime_type = refreshed["mime_type"]

            db.update_draft(
                draft_id,
                gemini_file_uri=video_uri,
                gemini_file_mime_type=mime_type,
            )

        cover_filename = f"{draft_id}.jpg"

        cover_path = (
            config.COVER_DIR / cover_filename
        )

        try:

            await asyncio.to_thread(
                generate_cover_from_uri,
                video_uri,
                mime_type,
                cover_path,
            )

        except GeminiError as first_error:

            message = str(first_error).lower()

            stale_reference = any(
                term in message
                for term in (
                    "not found",
                    "expired",
                    "404",
                    "invalid uri",
                    "file resource",
                )
            )

            if not stale_reference:
                raise

            from gemini_ai import upload_video_reference

            refreshed = await asyncio.to_thread(
                upload_video_reference,
                stored_path,
            )

            video_uri = refreshed["uri"]
            mime_type = refreshed["mime_type"]

            db.update_draft(
                draft_id,
                gemini_file_uri=video_uri,
                gemini_file_mime_type=mime_type,
            )

            await asyncio.to_thread(
                generate_cover_from_uri,
                video_uri,
                mime_type,
                cover_path,
            )

        db.update_draft(
            draft_id,
            cover_filename=cover_filename,
        )

        db.add_history(
            "Reels cover yaratildi",
            draft.get("filename", ""),
        )

        return {
            "ok": True,
            "cover_url": f"{config.APP_BASE_URL}/api/cover/{draft_id}",
            "filename": cover_filename,
        }

    except GeminiError as exc:

        db.add_history(
            "Reels cover yaratish",
            str(exc),
            "failed",
        )

        raise HTTPException(
            502,
            str(exc),
        ) from exc


# =========================================================
# COVER FILE
# =========================================================

@app.get("/api/cover/{draft_id}")
async def get_cover(draft_id: str):

    draft = db.get_draft(draft_id)

    if not draft or not draft.get("cover_filename"):
        raise HTTPException(
            404,
            "Cover topilmadi.",
        )

    path = (
        config.COVER_DIR
        / Path(draft["cover_filename"]).name
    )

    if not path.is_file():
        raise HTTPException(
            404,
            "Cover fayli mavjud emas.",
        )

    return FileResponse(
        path,
        media_type="image/jpeg",
        filename=path.name,
        content_disposition_type="inline",
    )


# =========================================================
# PUBLIC VIDEO
# =========================================================

@app.get("/media/public/{public_token}")
async def public_video(public_token: str):

    from database import _connect

    with _connect() as con:

        row = con.execute(
            """
            SELECT stored_path, filename
            FROM drafts
            WHERE public_token=?
            """,
            (public_token,),
        ).fetchone()

    if not row:
        raise HTTPException(
            404,
            "Video topilmadi.",
        )

    path = Path(
        row["stored_path"]
    ).resolve()

    if (
        not path.is_file()
        or config.UPLOAD_DIR.resolve() not in path.parents
    ):
        raise HTTPException(
            404,
            "Video fayli topilmadi.",
        )

    return FileResponse(
        path,
        media_type=(
            "video/mp4"
            if path.suffix.lower() == ".mp4"
            else "video/quicktime"
        ),
        filename=row["filename"],
    )


# =========================================================
# PUBLISH REELS TO INSTAGRAM
# =========================================================

@app.post("/api/reels/publish")
async def api_publish_reel(request: Request):

    connection = instagram_connection()

    if not connection:
        raise HTTPException(
            400,
            ".env faylida IG_ACCESS_TOKEN qiymati sozlanmagan.",
        )

    if not connection.get("user_id"):

        try:

            profile = get_profile(
                connection["token"]
            )

            connection["user_id"] = str(
                profile.get("user_id") or ""
            )

        except (
            InstagramAPIError,
            requests.RequestException,
        ) as exc:

            raise HTTPException(
                502,
                f"Instagram akkaunt ID olinmadi: {exc}",
            )

    if not connection.get("user_id"):
        raise HTTPException(
            400,
            ".env faylida IG_USER_ID ni kiriting.",
        )

    payload = await request.json()

    draft_id = str(
        payload.get("draft_id", "")
    )

    caption = str(
        payload.get("caption", "")
    ).strip()[:2200]

    hashtags = str(
        payload.get("hashtags", "")
    ).strip()[:500]

    share_to_feed = bool(
        payload.get("share_to_feed", True)
    )

    draft = db.get_draft(draft_id)

    if not draft:
        raise HTTPException(
            404,
            "Reels draft topilmadi.",
        )

    if draft["status"] == "published":
        raise HTTPException(
            409,
            "Bu draft allaqachon joylangan.",
        )

    if draft["status"] == "publishing":
        raise HTTPException(
            409,
            "Bu draft hozir Instagram'ga joylanmoqda.",
        )

    if not caption and hashtags:
        caption = hashtags

    elif hashtags:
        caption = f"{caption}\n\n{hashtags}"

    try:

        require_https_base()

        db.update_draft(
            draft_id,
            status="publishing",
        )

        public_url = (
            f"{config.APP_BASE_URL}/media/public/"
            f"{draft['public_token']}"
        )

        media_id, details = publish_reel(
            connection["token"],
            connection["user_id"],
            public_url,
            caption,
            share_to_feed,
        )

        db.update_draft(
            draft_id,
            caption=caption,
            status="published",
            instagram_media_id=media_id,
        )

        db.add_history(
            "Instagram Reels joylandi",
            f"{draft['filename']} | Media ID: {media_id}",
        )

        return {
            "ok": True,
            "media_id": media_id,
            "message": "Reels Instagram profilingizga joylandi.",
        }

    except (
        InstagramAPIError,
        HTTPException,
        requests.RequestException,
    ) as exc:

        message = (
            exc.detail
            if isinstance(exc, HTTPException)
            else str(exc)
        )

        db.update_draft(
            draft_id,
            status="draft",
        )

        db.add_history(
            "Reels joylash xatosi",
            message,
            "failed",
        )

        raise HTTPException(
            502 if not isinstance(exc, HTTPException)
            else exc.status_code,
            message,
        )


# =========================================================
# USER ACTIVITY
# =========================================================

@app.post("/api/activity")
async def api_activity(request: Request):

    data = await request.json()

    allowed = {
        "Til o‘zgartirildi",
        "Ko‘rinish rejimi o‘zgartirildi",
        "Profil matni nusxalandi",
        "Instagram profil tahriri ochildi",
        "Cover rasm ochildi",
    }

    action = str(
        data.get("action", "")
    ).strip()

    details = str(
        data.get("details", "")
    ).strip()

    if action not in allowed:
        raise HTTPException(
            400,
            "Bu faoliyat turi qabul qilinmaydi.",
        )

    db.add_history(
        action,
        details,
    )

    return {
        "ok": True,
    }


# =========================================================
# HISTORY
# =========================================================

@app.get("/api/history")
async def api_history():

    return {
        "items": db.get_history(250),
        "drafts": db.get_drafts(80),
    }


# =========================================================
# SYSTEM STATUS
# =========================================================

@app.get("/api/system/status")
async def system_status():

    base = urlparse(
        config.APP_BASE_URL
    )

    https_ok = (
        base.scheme == "https"
        and bool(base.netloc)
    )

    ig_status = {
        "ok": False,
        "label": ".env tokeni kiritilmagan",
    }

    if config.IG_ACCESS_TOKEN:

        try:

            profile = await asyncio.to_thread(
                get_profile,
                config.IG_ACCESS_TOKEN,
            )

            ig_status = {
                "ok": True,
                "label": "Instagram API faol",
                "username": profile.get("username", ""),
            }

        except Exception as exc:

            ig_status = {
                "ok": False,
                "label": "Instagram API xatosi",
                "detail": str(exc)[:180],
            }

    return {
        "https": {
            "ok": https_ok,
            "label": (
                "Backend HTTPS manzili sozlangan"
                if https_ok
                else "APP_BASE_URL HTTPS emas"
            ),
        },

        "instagram": ig_status,

        "gemini": {
            "ok": bool(config.GEMINI_API_KEY),
            "label": (
                "API key sozlangan"
                if config.GEMINI_API_KEY
                else "API key kiritilmagan"
            ),
        },

        "database": {
            "ok": config.DATABASE_PATH.exists(),
            "label": (
                "Ma’lumotlar bazasi tayyor"
                if config.DATABASE_PATH.exists()
                else "Baza hali yaratilmagan"
            ),
        },

        "app": {
            "ok": True,
            "label": "Ishlayapti",
            "version": config.APP_VERSION,
        },
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
async def health():

    return {
        "ok": True,
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
    }