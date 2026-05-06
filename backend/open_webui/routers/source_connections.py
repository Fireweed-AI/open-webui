from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from open_webui.models.external_source_connections import (
    ExternalSourceConnections,
)
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user
from open_webui.utils.external_sources.providers import (
    get_external_source_provider,
    get_provider_for_connection_provider,
    list_external_source_providers,
)


router = APIRouter()


class ConnectStartForm(BaseModel):
    next_path: str = "/admin/settings/documents"


class SourceConnectionUpdateForm(BaseModel):
    display_name: str | None = None
    knowledge_base_id: str | None = None
    access_control: dict | None = None
    selected_resources: list[dict] = Field(default_factory=list)


def _get_connection_files(connection_id: str):
    files = []
    for file in Files.get_files():
        meta_data = ((file.meta or {}).get("data") or {})
        if meta_data.get("external_source_connection_id") == connection_id:
            files.append(file)
    return files


def _delete_connection_files(connection_id: str) -> int:
    files = _get_connection_files(connection_id)
    count = 0
    for file in files:
        for knowledge in Knowledges.get_knowledges_by_file_id(file.id):
            Knowledges.remove_file_from_knowledge_by_id(knowledge.id, file.id)
        if file.path:
            try:
                Storage.delete_file(file.path)
            except Exception:
                pass
        Files.delete_file_by_id(file.id)
        count += 1
    return count


def _require_provider(provider_id: str):
    provider = get_external_source_provider(provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    return provider


def _get_connection_and_provider(connection_id: str, user_id: str):
    connection = ExternalSourceConnections.get_connection_by_id(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found.")
    if connection.user_id != user_id:
        raise HTTPException(status_code=404, detail="Connection not found.")

    provider = get_provider_for_connection_provider(connection.provider)
    if provider is None:
        raise HTTPException(status_code=400, detail="Unsupported provider.")

    return connection, provider


@router.get("/api/v1/integrations/providers")
async def list_source_providers(user=Depends(get_admin_user)):
    return {"providers": [provider.serialize() for provider in list_external_source_providers()]}


@router.get("/api/v1/integrations/connections")
async def list_source_connections(
    provider: str | None = Query(default=None), user=Depends(get_admin_user)
):
    provider_definition = None
    connection_provider = None
    if provider:
        provider_definition = _require_provider(provider)
        connection_provider = provider_definition.connection_provider

    connections = ExternalSourceConnections.get_connections(
        provider=connection_provider, user_id=user.id
    )
    serialized_connections = []
    for item in connections:
        item_provider = provider_definition or get_provider_for_connection_provider(item.provider)
        serialized_connections.append(
            item_provider.serialize_connection(item)
            if item_provider is not None
            else item.model_dump()
        )
    return {
        "connections": serialized_connections
    }


@router.post("/api/v1/integrations/providers/{provider}/connect/start")
async def start_provider_connect(
    provider: str,
    request: Request,
    form_data: ConnectStartForm,
    user=Depends(get_admin_user),
):
    provider_definition = _require_provider(provider)
    return {
        "authorize_url": await provider_definition.build_authorize_url(
            request, user.id, form_data.next_path
        )
    }


@router.get(
    "/api/v1/integrations/providers/{provider}/connect/callback",
    name="source_connection_provider_callback",
)
async def source_connection_provider_callback(
    provider: str, request: Request, code: str = "", state: str = ""
):
    if not code or not state:
        raise HTTPException(
            status_code=400, detail="Missing provider callback parameters."
        )

    provider_definition = _require_provider(provider)
    connection, next_path = await provider_definition.complete_connection_callback(
        request, code, state
    )

    separator = "&" if "?" in next_path else "?"
    return RedirectResponse(
        url=f"{next_path}{separator}{provider_definition.callback_query_key}={connection.id}",
        status_code=302,
    )


@router.get("/api/v1/integrations/connections/{connection_id}")
async def get_source_connection(connection_id: str, user=Depends(get_admin_user)):
    connection, provider = _get_connection_and_provider(connection_id, user.id)
    return provider.serialize_connection(connection)


@router.post("/api/v1/integrations/connections/{connection_id}")
async def update_source_connection(
    connection_id: str,
    form_data: SourceConnectionUpdateForm,
    request: Request,
    user=Depends(get_admin_user),
):
    connection, provider = _get_connection_and_provider(connection_id, user.id)
    updated = await provider.update_connection(
        request, connection, form_data.model_dump()
    )
    return provider.serialize_connection(updated)


@router.get("/api/v1/integrations/connections/{connection_id}/selection-token")
async def get_connection_selection_token(
    request: Request, connection_id: str, user=Depends(get_admin_user)
):
    connection, provider = _get_connection_and_provider(connection_id, user.id)
    return await provider.get_selection_token(request, connection)


@router.post("/api/v1/integrations/connections/{connection_id}/sync")
async def sync_source_connection(
    request: Request, connection_id: str, user=Depends(get_admin_user)
):
    connection, provider = _get_connection_and_provider(connection_id, user.id)
    return await provider.sync_connection(request, connection)


@router.get("/api/v1/integrations/connections/{connection_id}/preview")
async def preview_source_connection(
    request: Request, connection_id: str, user=Depends(get_admin_user)
):
    connection, provider = _get_connection_and_provider(connection_id, user.id)
    return await provider.preview_selection(request, connection)


@router.get("/api/v1/integrations/connections/{connection_id}/files")
async def list_connection_files(connection_id: str, user=Depends(get_admin_user)):
    connection, _provider = _get_connection_and_provider(connection_id, user.id)
    files = _get_connection_files(connection.id)
    return {"count": len(files), "files": files}


@router.delete("/api/v1/integrations/connections/{connection_id}/files")
async def delete_connection_files(connection_id: str, user=Depends(get_admin_user)):
    connection, _provider = _get_connection_and_provider(connection_id, user.id)
    deleted = _delete_connection_files(connection.id)
    return {"status": True, "connection_id": connection.id, "deleted": deleted}


@router.delete("/api/v1/integrations/connections/{connection_id}")
async def delete_source_connection(connection_id: str, user=Depends(get_admin_user)):
    connection, _provider = _get_connection_and_provider(connection_id, user.id)

    _delete_connection_files(connection.id)
    if connection.oauth_session_id:
        OAuthSessions.delete_session_by_id(connection.oauth_session_id)

    deleted = ExternalSourceConnections.delete_connection_by_id(connection.id)
    return {"status": deleted, "connection_id": connection.id}
