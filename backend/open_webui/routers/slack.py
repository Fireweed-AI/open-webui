import asyncio
import hashlib
import hmac
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from open_webui.utils.platform_integrations import run_platform_chat


log = logging.getLogger(__name__)

router = APIRouter()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "").strip()


def _verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    if not SLACK_SIGNING_SECRET or not timestamp or not signature:
        return False

    if abs(time.time() - int(timestamp)) > 300:
        return False

    base = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _post_message(channel: str, text: str, thread_ts: str | None = None) -> None:
    if not SLACK_BOT_TOKEN:
        log.error("SLACK_BOT_TOKEN is not configured")
        return

    payload: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json=payload,
            timeout=15,
        )

    data = response.json()
    if not data.get("ok"):
        log.error("Slack postMessage failed: %s", response.text)


def _parse_slash_command(text: str) -> tuple[str, str]:
    text = text.strip()
    if not text or text.lower() == "help":
        return "help", ""

    lower = text.lower()
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


HELP_TEXT = """*Fireweed AI*

`/fireweed <message>` chat with Fireweed AI
`/fireweed translate <word>` English to Teetl'it Gwich'in
`/fireweed translate gwi <word>` Teetl'it Gwich'in to English
`/fireweed help` show this help
"""


async def _handle_chat(
    request: Request,
    channel: str,
    prompt: str,
    conversation_id: str,
    thread_ts: str | None,
) -> None:
    try:
        text = await run_platform_chat(
            request=request,
            prompt=prompt,
            platform="slack",
            conversation_id=conversation_id,
        )
        await _post_message(channel, text, thread_ts)
    except Exception:
        log.exception("Slack chat handler failed")
        await _post_message(
            channel,
            "Sorry, something went wrong while processing that request.",
            thread_ts,
        )


@router.post("/api/v1/integrations/slack/events")
async def slack_events(
    request: Request,
    x_slack_request_timestamp: str = Header(default=""),
    x_slack_signature: str = Header(default=""),
):
    body = await request.body()

    if SLACK_SIGNING_SECRET and not _verify_slack_signature(
        body, x_slack_request_timestamp, x_slack_signature
    ):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    payload = await request.json()
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload["challenge"]})

    event = payload.get("event", {})
    if event.get("bot_id"):
        return JSONResponse({"ok": True})

    if event.get("type") in {"app_mention", "message"}:
        text = str(event.get("text", "")).strip()
        channel = str(event.get("channel", "")).strip()
        thread_ts = event.get("thread_ts") or event.get("ts")

        if "<@" in text:
            text = text.split(">", 1)[-1].strip()

        if text and channel:
            conversation_id = f"{channel}:{thread_ts or ''}"
            asyncio.create_task(
                _handle_chat(request, channel, text, conversation_id, thread_ts)
            )

    return JSONResponse({"ok": True})


@router.post("/api/v1/integrations/slack/commands")
async def slack_commands(
    request: Request,
    x_slack_request_timestamp: str = Header(default=""),
    x_slack_signature: str = Header(default=""),
):
    body = await request.body()

    if SLACK_SIGNING_SECRET and not _verify_slack_signature(
        body, x_slack_request_timestamp, x_slack_signature
    ):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    form = await request.form()
    text = str(form.get("text", "")).strip()
    channel = str(form.get("channel_id", "")).strip()
    thread_ts = None

    action, payload = _parse_slash_command(text)
    if action == "help":
        return JSONResponse({"response_type": "ephemeral", "text": HELP_TEXT})

    if action == "translate_en_gwi":
        prompt = _translate_prompt(payload, "en", "gwi")
        ack = f"_Translating_ *{payload}* _from English to Teetl'it Gwich'in..._"
    elif action == "translate_gwi_en":
        prompt = _translate_prompt(payload, "gwi", "en")
        ack = f"_Translating_ *{payload}* _from Teetl'it Gwich'in to English..._"
    else:
        prompt = payload
        ack = "_Fireweed AI is thinking..._"

    if channel:
        conversation_id = f"{channel}:slash"
        asyncio.create_task(
            _handle_chat(request, channel, prompt, conversation_id, thread_ts)
        )

    return JSONResponse({"response_type": "in_channel", "text": ack})


@router.get("/api/v1/integrations/slack/health")
async def slack_health():
    return {"status": True, "integration": "slack"}
