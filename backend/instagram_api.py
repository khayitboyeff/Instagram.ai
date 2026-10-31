import requests

from config import IG_GRAPH_VERSION

GRAPH_BASE = "https://graph.instagram.com"
TIMEOUT = 45


class InstagramAPIError(RuntimeError):
    pass


def _raise_api(response: requests.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        raise InstagramAPIError(f"Instagram API javobi tushunarsiz (HTTP {response.status_code}).")
    if not response.ok or data.get("error"):
        err = data.get("error", data)
        message = err.get("message", "Instagram API xatosi") if isinstance(err, dict) else str(err)
        raise InstagramAPIError(message)
    return data


def graph_get(path: str, token: str, params: dict | None = None) -> dict:
    query = dict(params or {})
    query["access_token"] = token
    url = f"{GRAPH_BASE}/{IG_GRAPH_VERSION}/{path.lstrip('/')}"
    response = requests.get(url, params=query, timeout=TIMEOUT)
    return _raise_api(response)


def graph_post(path: str, token: str, data: dict) -> dict:
    payload = dict(data)
    payload["access_token"] = token
    url = f"{GRAPH_BASE}/{IG_GRAPH_VERSION}/{path.lstrip('/')}"
    response = requests.post(url, data=payload, timeout=TIMEOUT)
    return _raise_api(response)


def get_profile(token: str) -> dict:
    return graph_get("me", token, {"fields": "user_id,username,name,account_type,media_count,followers_count,follows_count,profile_picture_url,biography,website"})


def get_recent_media(token: str, limit: int = 25) -> list[dict]:
    data = graph_get("me/media", token, {
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink,thumbnail_url,media_url,like_count,comments_count",
        "limit": limit,
    })
    return data.get("data", [])


def get_account_insights(token: str) -> dict:
    metrics = ["views", "reach", "accounts_engaged", "total_interactions"]
    try:
        data = graph_get("me/insights", token, {
            "metric": ",".join(metrics), "period": "day", "metric_type": "total_value"
        })
        output = {}
        for item in data.get("data", []):
            total = item.get("total_value") or {}
            values = item.get("values") or []
            value = total.get("value") if isinstance(total, dict) else None
            if value is None and values:
                value = values[0].get("value")
            output[item.get("name")] = value
        return output
    except InstagramAPIError:
        return {}


def get_media_insights(token: str, media_id: str) -> dict:
    metrics = ["views", "reach", "likes", "comments", "saved", "shares", "total_interactions"]
    try:
        data = graph_get(f"{media_id}/insights", token, {"metric": ",".join(metrics)})
        return {item.get("name"): (item.get("values") or [{}])[0].get("value") for item in data.get("data", [])}
    except InstagramAPIError:
        # Metric names vary for some media types and account configurations.
        return {}


def publish_reel(token: str, user_id: str, public_video_url: str, caption: str, share_to_feed: bool = True) -> tuple[str, dict]:
    container = graph_post(f"{user_id}/media", token, {
        "media_type": "REELS",
        "video_url": public_video_url,
        "caption": caption,
        "share_to_feed": "true" if share_to_feed else "false",
    })
    container_id = container.get("id")
    if not container_id:
        raise InstagramAPIError("Instagram video container ID qaytarmadi.")

    import time
    last_status = {}
    for _ in range(24):
        last_status = graph_get(container_id, token, {"fields": "status_code,status"})
        status = str(last_status.get("status_code", "")).upper()
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramAPIError(last_status.get("status", "Instagram videoni qayta ishlay olmadi."))
        time.sleep(5)
    else:
        raise InstagramAPIError("Instagram videoni qayta ishlashi kutilgan vaqtda tugamadi. Qayta urinib ko‘rishdan oldin draft holatini tekshiring.")

    result = graph_post(f"{user_id}/media_publish", token, {"creation_id": container_id})
    media_id = str(result.get("id", ""))
    return media_id, {"container": container, "status": last_status, "publish": result}


def refresh_token(token: str) -> dict:
    response = requests.get(f"{GRAPH_BASE}/refresh_access_token", params={
        "grant_type": "ig_refresh_token", "access_token": token
    }, timeout=TIMEOUT)
    return _raise_api(response)
