"""Gemini workflow: fast text result first, optional cover generation second."""
from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

from config import (
    GEMINI_API_KEY,
    GEMINI_VIDEO_MODEL,
    GEMINI_CONTENT_MODEL,
    GEMINI_IMAGE_MODEL,
)


class GeminiError(RuntimeError):
    """A safe, user-readable Gemini API error."""


def _client():
    if not GEMINI_API_KEY:
        raise GeminiError("Gemini API Key .env faylida kiritilmagan.")
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:
        raise GeminiError(f"Gemini SDK ishga tushmadi: {exc}") from exc


def _interaction_text(interaction: Any) -> str:
    value = getattr(interaction, "output_text", None)
    if value:
        return str(value).strip()
    chunks: list[str] = []
    for step in getattr(interaction, "steps", []) or []:
        for block in getattr(step, "content", []) or []:
            if getattr(block, "type", "") == "text":
                chunks.append(str(getattr(block, "text", "")))
    return "\n".join(chunks).strip()


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if match:
            try:
                value = json.loads(match.group(0))
                return value if isinstance(value, dict) else {}
            except json.JSONDecodeError:
                pass
    return {}


def _upload_video(client: Any, video_path: Path) -> Any:
    try:
        file_obj = client.files.upload(file=str(video_path))
        state = getattr(getattr(file_obj, "state", None), "name", "")
        for _ in range(60):
            if state != "PROCESSING":
                break
            time.sleep(2)
            file_obj = client.files.get(name=file_obj.name)
            state = getattr(getattr(file_obj, "state", None), "name", "")
        if state == "FAILED":
            raise GeminiError("Gemini videoni qayta ishlay olmadi. Boshqa MP4/MOV video bilan urinib ko‘ring.")
        if state and state not in {"PROCESSING", "ACTIVE", "READY"}:
            raise GeminiError(f"Gemini video fayl holatini tasdiqlamadi: {state}")
        if state == "PROCESSING":
            raise GeminiError("Video Gemini’da hali tayyor bo‘lmadi. Birozdan keyin qayta urinib ko‘ring.")
        if not getattr(file_obj, "uri", None):
            raise GeminiError("Gemini video URI manzilini qaytarmadi.")
        return file_obj
    except GeminiError:
        raise
    except Exception as exc:
        raise GeminiError(f"Videoni Gemini’ga yuklashda xato: {exc}") from exc


def _normalise_hashtags(value: Any) -> list[str]:
    if isinstance(value, str):
        parts = value.split()
    elif isinstance(value, list):
        parts = value
    else:
        parts = []
    tags = []
    for item in parts:
        tag = re.sub(r"[^\w#]", "", str(item).strip(), flags=re.UNICODE)
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag
        if tag not in tags:
            tags.append(tag)
        if len(tags) >= 15:
            break
    return tags



def upload_video_reference(video_path: Path) -> dict[str, str]:
    """Upload a saved local video to Gemini and return its reusable file reference."""
    client = _client()
    uploaded = _upload_video(client, Path(video_path))
    mime_type = getattr(uploaded, "mime_type", None) or (
        "video/quicktime" if Path(video_path).suffix.lower() == ".mov" else "video/mp4"
    )
    return {"uri": str(uploaded.uri), "mime_type": str(mime_type)}


def analyze_video(video_path: Path) -> dict[str, Any]:
    """Analyse uploaded video and return text only; never wait for image generation."""
    client = _client()
    uploaded = _upload_video(client, Path(video_path))
    mime_type = getattr(uploaded, "mime_type", None) or (
        "video/quicktime" if Path(video_path).suffix.lower() == ".mov" else "video/mp4"
    )
    video_uri = uploaded.uri

    video_prompt = """Videoni qisqa va diqqat bilan tahlil qil. Faqat ko‘rinadigan yoki eshitiladigan faktlarga tayan. Javobni FAQAT valid JSON ko‘rinishida, o‘zbek lotin tilida ber:
{
  "video_summary": "1-2 gapda videoda nima borligi",
  "visual_facts": "asosiy obyektlar, harakat, ranglar va kayfiyat; uydirma faktlarsiz",
  "fallback_caption": "tabiiy, qisqa Instagram caption",
  "fallback_hashtags": ["#mavzugaMos", "#reels"]
}
Ism, joy, mahsulot yoki voqeani videoda aniq ko‘rinmasa uydirma. Ortiqcha emoji va yolg‘on da’volardan saqlan."""
    try:
        video_result = client.interactions.create(
            model=GEMINI_VIDEO_MODEL,
            input=[
                {"type": "video", "uri": video_uri, "mime_type": mime_type},
                {"type": "text", "text": video_prompt},
            ],
        )
        facts = _extract_json(_interaction_text(video_result))
        summary = str(facts.get("video_summary", "")).strip()[:1000]
        visual_facts = str(facts.get("visual_facts", summary)).strip()[:1600]
    except Exception as exc:
        if isinstance(exc, GeminiError):
            raise
        raise GeminiError(f"Videoni tahlil qilishda Gemini xatosi: {exc}") from exc

    fallback_caption = str(facts.get("fallback_caption", "")).strip()[:2200]
    fallback_tags = _normalise_hashtags(facts.get("fallback_hashtags", []))

    content_prompt = f"""Quyidagi tayyor video tavsifidan foydalanib Instagram Reels uchun kontent to‘plami tuz.
Video xulosasi: {summary}
Ko‘rinadigan faktlar: {visual_facts}

Faqat o‘zbek lotin tilida va FAQAT valid JSON qaytar:
{{
  "caption": "tabiiy, o‘ziga xos, mavzuga mos caption; yolg‘on da’vo va ortiqcha emojilarsiz",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8"],
  "content_prompt": "videodagi mavzuga mos, boshqa AI vositasida ishlatishga tayyor professional prompt"
}}
Caption videodagi aniq mazmunga mos bo‘lsin. Hashtaglar mavzuga aloqador bo‘lsin. Promptda videoda ko‘rsatilmagan odam, joy yoki mahsulotni qo‘shma. Izoh yoki markdown yozma."""
    content_data: dict[str, Any] = {}
    try:
        content_result = client.interactions.create(
            model=GEMINI_CONTENT_MODEL,
            input=content_prompt,
        )
        content_data = _extract_json(_interaction_text(content_result))
    except Exception:
        # Keep a usable text result if the lightweight content model is temporarily unavailable.
        content_data = {}

    return {
        "video_summary": summary,
        "caption": str(content_data.get("caption") or fallback_caption)[:2200],
        "hashtags": _normalise_hashtags(content_data.get("hashtags") or fallback_tags),
        "content_prompt": (str(content_data.get("content_prompt", "")).strip()
                           or f"Quyidagi videodagi mavzu asosida sifatli, tabiiy va vertikal 9:16 kontent yarating. Asosiy mazmun: {visual_facts}")[:4000],
        "gemini_file_uri": str(video_uri),
        "gemini_file_mime_type": str(mime_type),
    }


def generate_cover_from_uri(video_uri: str, mime_type: str, cover_path: Path) -> None:
    """Generate a Reel cover on demand; this call is deliberately outside video analysis."""
    if not video_uri:
        raise GeminiError("Gemini video manzili topilmadi. Videoni AI bilan qayta tahlil qiling.")
    client = _client()
    image_prompt = "Videoning haqiqiy mavzusi, obyektlari, ranglari va kayfiyatiga mos Instagram Reels cover yarat. Vertikal 9:16 kompozitsiya. Minimal, premium, toza vizual uslub; asosiy obyekt markazga yaqin va aniq ko‘rinsin. Matn, logo, watermark va videoda bo‘lmagan odam yoki predmet qo‘shma."
    try:
        interaction = client.interactions.create(
            model=GEMINI_IMAGE_MODEL,
            input=[
                {"type": "video", "uri": video_uri, "mime_type": mime_type or "video/mp4"},
                {"type": "text", "text": image_prompt},
            ],
            response_format={"type": "image", "mime_type": "image/jpeg", "aspect_ratio": "9:16", "image_size": "1K"},
        )
        image_data = getattr(getattr(interaction, "output_image", None), "data", None)
        if not image_data:
            for step in getattr(interaction, "steps", []) or []:
                for block in getattr(step, "content", []) or []:
                    if getattr(block, "type", "") == "image" and getattr(block, "data", None):
                        image_data = block.data
                        break
                if image_data:
                    break
        if not image_data:
            raise GeminiError("Gemini rasm natijasini qaytarmadi. Qayta urinib ko‘ring.")
        cover_path = Path(cover_path)
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        cover_path.write_bytes(base64.b64decode(image_data))
    except GeminiError:
        raise
    except Exception as exc:
        raise GeminiError(f"Cover yaratishda Gemini xatosi: {exc}") from exc
