import httpx
from app.config import settings

CATEGORY_KEYWORDS = {
    "garbage_black_spot": ["garbage", "trash", "waste", "dump", "black spot", "refuse", "littering", "ಕಸ"],
    "cd_waste": ["construction", "demolition", "debris", "rubble", "cement", "bricks", "sand"],
    "waterlogging": ["flood", "waterlog", "puddle", "stagnant", "overflow", "rain water", "ನೀರು"],
    "drain_blockage": ["drain", "blocked", "clog", "sewage", "manhole", "stormwater", "rajakaluves"],
    "groundwater": ["borewell", "groundwater", "water shortage", "dry", "no water", "tanker"],
}

SLA_HOURS = {
    "critical": 4,
    "high": 24,
    "medium": 72,
    "low": 168,
}


def classify_complaint_local(title: str, description: str = "") -> dict:
    """Fallback rule-based classifier when watsonx is not configured."""
    text = (title + " " + (description or "")).lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1

    best_cat = max(scores, key=scores.get)
    confidence = min(scores[best_cat] / 3.0, 1.0) if scores[best_cat] > 0 else 0.4
    if confidence == 0.4:
        best_cat = "other"

    priority = "medium"
    if any(w in text for w in ["urgent", "critical", "emergency", "flood", "overflow"]):
        priority = "critical"
    elif any(w in text for w in ["high", "dangerous", "hazard"]):
        priority = "high"
    elif any(w in text for w in ["minor", "small", "low"]):
        priority = "low"

    return {
        "category": best_cat,
        "priority": priority,
        "confidence": round(confidence, 2),
        "summary": f"Complaint classified as '{best_cat}' with {round(confidence*100)}% confidence.",
    }


async def classify_with_watsonx(title: str, description: str = "") -> dict:
    """Call IBM watsonx.ai for NLP classification."""
    if not settings.WATSONX_API_KEY or not settings.WATSONX_PROJECT_ID:
        return classify_complaint_local(title, description)

    prompt = f"""Classify the following civic complaint into one of these categories:
garbage_black_spot, cd_waste, waterlogging, drain_blockage, groundwater, other.
Also assign a priority: low, medium, high, critical.
Provide a one-sentence summary.

Complaint: {title}. {description}

Respond in JSON: {{"category": "...", "priority": "...", "confidence": 0.0, "summary": "..."}}"""

    try:
        # Get IAM token
        async with httpx.AsyncClient() as client:
            iam_resp = await client.post(
                "https://iam.cloud.ibm.com/identity/token",
                data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": settings.WATSONX_API_KEY},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            iam_token = iam_resp.json().get("access_token")

            resp = await client.post(
                f"{settings.WATSONX_URL}/ml/v1/text/generation?version=2023-05-29",
                json={
                    "model_id": "ibm/granite-13b-instruct-v2",
                    "input": prompt,
                    "parameters": {"max_new_tokens": 150, "temperature": 0.1},
                    "project_id": settings.WATSONX_PROJECT_ID,
                },
                headers={"Authorization": f"Bearer {iam_token}", "Content-Type": "application/json"},
                timeout=15,
            )
            result_text = resp.json()["results"][0]["generated_text"]
            import json, re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception:
        pass

    return classify_complaint_local(title, description)


async def analyze_media(url: str, mime_type: str = "") -> str:
    """
    Return a plain-English description of an image/video/audio attachment.

    If watsonx Speech-to-Text or Vision is not configured, returns a generic
    placeholder so the rest of the pipeline can continue without crashing.
    """
    # Minimal implementation: for now return a placeholder.
    # A full implementation would call watsonx Vision or speech APIs here.
    if not settings.WATSONX_API_KEY:
        return f"[Media attachment — type: {mime_type or 'unknown'}]"

    # Stub: real call would go to watsonx Vision endpoint
    return f"[AI analysis of media at {url[:60]}...]"


async def transcribe_voice(audio_url: str) -> str:
    """
    Transcribe a voice recording URL to text using watsonx Speech-to-Text.

    Falls back to an empty string if not configured.
    """
    if not settings.WATSONX_API_KEY:
        return ""

    # Stub: real call would POST audio_url to watsonx Speech-to-Text
    return ""
