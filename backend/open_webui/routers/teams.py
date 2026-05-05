import asyncio
import logging
import os
import re
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from open_webui.utils.platform_integrations import run_platform_chat


log = logging.getLogger(__name__)

router = APIRouter()

TEAMS_APP_ID = os.environ.get("TEAMS_APP_ID", "").strip()
TEAMS_APP_PASSWORD = os.environ.get("TEAMS_APP_PASSWORD", "").strip()

_token_cache: dict[str, float | str] = {}


async def _get_bot_token() -> str:
    cached = _token_cache.get("token")
    expires = float(_token_cache.get("expires", 0))

    if cached and time.time() < expires - 60:
        return str(cached)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": TEAMS_APP_ID,
                "client_secret": TEAMS_APP_PASSWORD,
                "scope": "https://api.botframework.com/.default",
            },
            timeout=15,
        )

    response.raise_for_status()
    payload = response.json()
    token = payload["access_token"]
    _token_cache["token"] = token
    _token_cache["expires"] = time.time() + payload.get("expires_in", 3600)
    return token


async def _send_reply(
    service_url: str,
    conversation_id: str,
    activity_id: str,
    text: str,
) -> None:
    token = await _get_bot_token()
    url = (
        f"{service_url.rstrip('/')}/v3/conversations/"
        f"{conversation_id}/activities/{activity_id}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "message", "text": text, "textFormat": "markdown"},
            timeout=15,
        )

    if response.status_code not in (200, 201):
        log.error("Teams reply failed: %s %s", response.status_code, response.text)


def _parse_teams_message(text: str) -> tuple[str, str]:
    text = re.sub(r"<[^>]+>", "", text).strip()
    lower = text.lower()

    if not lower or lower == "help":
        return "help", ""
    if lower.startswith("translate gwi "):
        return "translate_gwi_en", text[len("translate gwi ") :]
    if lower.startswith("translate "):
        return "translate_en_gwi", text[len("translate ") :]

    return "chat", text


def _translate_prompt(text: str, source: str, target: str) -> str:
    languages = {"en": "English", "gwi": "Teetl'it Gwich'in"}
    return (
        f"Translate the following from {languages[source]} to {languages[target]}. "
        f"Reply with only the translation and no explanation: {text}"
    )


HELP_TEXT = """**Fireweed AI**

**Chat:** send any message
**Translate:** `translate <word>`
**Translate:** `translate gwi <word>`
**Help:** `help`
"""


async def _process_activity(request: Request, activity: dict) -> None:
    activity_type = activity.get("type", "")
    service_url = activity.get("serviceUrl", "")
    conversation_id = activity.get("conversation", {}).get("id", "")
    activity_id = activity.get("id", "")

    if activity_type == "conversationUpdate":
        members_added = activity.get("membersAdded", [])
        bot_id = activity.get("recipient", {}).get("id", "")
        for member in members_added:
            if member.get("id") != bot_id:
                await _send_reply(
                    service_url,
                    conversation_id,
                    activity_id,
                    "Mahsi' choo. I'm Fireweed AI. Type `help` to get started.",
                )
        return

    if activity_type != "message":
        return

    text = str(activity.get("text", "")).strip()
    if not text:
        return

    action, payload = _parse_teams_message(text)
    if action == "help":
        await _send_reply(service_url, conversation_id, activity_id, HELP_TEXT)
        return

    prompt = payload
    if action == "translate_en_gwi":
        prompt = _translate_prompt(payload, "en", "gwi")
    elif action == "translate_gwi_en":
        prompt = _translate_prompt(payload, "gwi", "en")

    try:
        response_text = await run_platform_chat(
            request=request,
            prompt=prompt,
            platform="teams",
            conversation_id=conversation_id,
        )
    except Exception:
        log.exception("Teams activity handler failed")
        response_text = "Sorry, something went wrong while processing that request."

    await _send_reply(service_url, conversation_id, activity_id, response_text)


@router.post("/api/v1/integrations/teams/messages")
async def teams_messages(request: Request):
    if not TEAMS_APP_ID or not TEAMS_APP_PASSWORD:
        return JSONResponse(
            {"detail": "Teams integration is not configured."},
            status_code=503,
        )

    try:
        activity = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)

    asyncio.create_task(_process_activity(request, activity))
    return JSONResponse({}, status_code=200)


@router.get("/api/v1/integrations/teams/health")
async def teams_health():
    return {"status": True, "integration": "teams"}
