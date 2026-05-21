import json
import os
from typing import Any

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from open_webui.models.users import Users, UserModel
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.models import get_all_models


INTEGRATIONS_MODEL_ID = os.environ.get("INTEGRATIONS_MODEL_ID", "").strip()


def get_integration_user() -> UserModel:
    user = Users.get_super_admin_user() or Users.get_first_user()
    if user is None:
        raise HTTPException(
            status_code=503,
            detail="No Open WebUI user is available for platform integrations.",
        )
    return user


async def get_integration_model_id(request: Request, user: UserModel) -> str:
    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    models = request.app.state.MODELS or {}
    if not models:
        raise HTTPException(status_code=503, detail="No models are available.")

    if INTEGRATIONS_MODEL_ID and INTEGRATIONS_MODEL_ID in models:
        return INTEGRATIONS_MODEL_ID

    default_models = request.app.state.config.DEFAULT_MODELS
    if isinstance(default_models, str) and default_models in models:
        return default_models

    if isinstance(default_models, list):
        for model_id in default_models:
            if model_id in models:
                return model_id

    return next(iter(models))


def extract_chat_text(result: Any) -> str:
    payload = result

    if isinstance(result, JSONResponse):
        payload = json.loads(result.body.decode("utf-8"))

    if isinstance(payload, dict):
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()

        if isinstance(payload.get("response"), str):
            return payload["response"].strip()

        if isinstance(payload.get("content"), str):
            return payload["content"].strip()

    return str(payload).strip()


async def run_platform_chat(
    request: Request,
    prompt: str,
    platform: str,
    conversation_id: str,
) -> str:
    user = get_integration_user()
    model_id = await get_integration_model_id(request, user)

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "metadata": {
            "integration": platform,
            "platform_conversation_id": conversation_id,
        },
    }

    result = await generate_chat_completion(request, form_data=payload, user=user)
    return extract_chat_text(result)
