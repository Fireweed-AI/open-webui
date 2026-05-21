import asyncio
import json
import logging
import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user
from open_webui.utils.platform_integrations import get_integration_user
from open_webui.utils.source_sync import ensure_knowledge_base, upsert_external_file


log = logging.getLogger(__name__)

router = APIRouter()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_sharepoint_token_cache: dict[str, float | str] = {}


class GDriveSyncRequest(BaseModel):
    folder_id: str | None = None
    knowledge_base_id: str | None = None
    access_control: dict | None = None


class SharePointSyncRequest(BaseModel):
    site_url: str | None = None
    knowledge_base_id: str | None = None
    access_control: dict | None = None


class GDriveConfigForm(BaseModel):
    enabled: bool
    service_account_json: str = ""
    watch_folder_id: str = ""
    webhook_token: str = ""
    knowledge_base_id: str = ""
    access_control: dict | None = Field(default_factory=dict)


class SharePointConfigForm(BaseModel):
    enabled: bool
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    site_url: str = ""
    knowledge_base_id: str = ""
    access_control: dict | None = Field(default_factory=dict)


class SourcesConfigForm(BaseModel):
    gdrive: GDriveConfigForm
    sharepoint: SharePointConfigForm


def _get_source_files(source: str):
    files = []
    for file in Files.get_files():
        meta_data = ((file.meta or {}).get("data") or {})
        if meta_data.get("external_source") == source:
            files.append(file)
    return files


def _delete_source_files(source: str) -> int:
    files = _get_source_files(source)
    count = 0
    for file in files:
        for knowledge in Knowledges.get_knowledges_by_file_id(file.id):
            Knowledges.remove_file_from_knowledge_by_id(knowledge.id, file.id)
        if file.path:
            try:
                Storage.delete_file(file.path)
            except Exception:
                log.exception("Failed to delete stored source file")
        Files.delete_file_by_id(file.id)
        count += 1
    return count


def _current_config(request: Request) -> dict:
    return {
        "gdrive": {
            "enabled": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
            "service_account_json": request.app.state.config.GDRIVE_SERVICE_ACCOUNT_JSON,
            "watch_folder_id": request.app.state.config.GDRIVE_WATCH_FOLDER_ID,
            "webhook_token": request.app.state.config.GDRIVE_WEBHOOK_TOKEN,
            "knowledge_base_id": request.app.state.config.GDRIVE_KNOWLEDGE_ID,
            "access_control": request.app.state.config.GDRIVE_ACCESS_CONTROL,
        },
        "sharepoint": {
            "enabled": request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
            "tenant_id": request.app.state.config.SHAREPOINT_TENANT_ID,
            "client_id": request.app.state.config.SHAREPOINT_CLIENT_ID,
            "client_secret": request.app.state.config.SHAREPOINT_CLIENT_SECRET,
            "site_url": request.app.state.config.SHAREPOINT_SITE_URL,
            "knowledge_base_id": request.app.state.config.SHAREPOINT_KNOWLEDGE_ID,
            "access_control": request.app.state.config.SHAREPOINT_ACCESS_CONTROL,
        },
    }


async def _get_drive_token(request: Request) -> str:
    service_account_json = request.app.state.config.GDRIVE_SERVICE_ACCOUNT_JSON
    if not service_account_json:
        raise HTTPException(status_code=503, detail="Google Drive is not configured.")

    try:
        import google.auth.transport.requests as ga_requests
        import google.oauth2.service_account as sa
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="google-auth is required.") from exc

    try:
        service_account_info = json.loads(service_account_json)
        credentials = sa.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
    except json.JSONDecodeError:
        credentials = sa.Credentials.from_service_account_file(
            service_account_json,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )

    credentials.refresh(ga_requests.Request())
    return credentials.token


async def _list_drive_files(request: Request, folder_id: str) -> list[dict]:
    token = await _get_drive_token(request)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "files(id,name,mimeType,modifiedTime,size)",
                "pageSize": 100,
            },
            timeout=30,
        )
    response.raise_for_status()
    return response.json().get("files", [])


async def _download_drive_file(
    request: Request, file_id: str, mime_type: str
) -> tuple[bytes, str, str | None]:
    token = await _get_drive_token(request)
    export_map = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }

    async with httpx.AsyncClient() as client:
        if mime_type in export_map:
            export_type = export_map[mime_type]
            response = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                headers={"Authorization": f"Bearer {token}"},
                params={"mimeType": export_type},
                timeout=60,
            )
            response.raise_for_status()
            return response.content, export_type, response.text

        response = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
    response.raise_for_status()
    text_content = None
    if mime_type.startswith("text/") or mime_type == "application/json":
        text_content = response.text
    return response.content, mime_type or "application/octet-stream", text_content


async def _sync_gdrive_folder(
    request: Request,
    folder_id: str,
    knowledge_base_id: str | None,
    access_control: dict | None,
) -> dict:
    user = get_integration_user()
    resolved_access_control = (
        access_control
        if access_control is not None
        else request.app.state.config.GDRIVE_ACCESS_CONTROL
    )
    knowledge_id = ensure_knowledge_base(
        user,
        knowledge_base_id or request.app.state.config.GDRIVE_KNOWLEDGE_ID or None,
        "Google Drive Sync",
        "Documents synchronized from Google Drive.",
        resolved_access_control,
    )

    files = await _list_drive_files(request, folder_id)
    synced = 0
    skipped = 0
    for file in files:
        mime_type = file.get("mimeType", "")
        if mime_type.startswith("application/vnd.google-apps.folder"):
            skipped += 1
            continue

        content_bytes, content_type, text_content = await _download_drive_file(
            request, file["id"], mime_type
        )
        filename = file["name"]
        if mime_type == "application/vnd.google-apps.document":
            filename = f"{filename}.txt"
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            filename = f"{filename}.csv"
        elif mime_type == "application/vnd.google-apps.presentation":
            filename = f"{filename}.txt"

        upsert_external_file(
            request=request,
            user=user,
            knowledge_id=knowledge_id,
            source="gdrive",
            external_id=file["id"],
            filename=filename,
            content_bytes=content_bytes,
            content_type=content_type,
            extra_meta={
                "folder_id": folder_id,
                "modified_time": file.get("modifiedTime"),
            },
            process_content=text_content,
            access_control=resolved_access_control,
        )
        synced += 1

    return {
        "status": True,
        "source": "gdrive",
        "knowledge_base_id": knowledge_id,
        "folder_id": folder_id,
        "access_control": resolved_access_control,
        "synced": synced,
        "skipped": skipped,
    }


async def _get_graph_token(request: Request) -> str:
    tenant_id = request.app.state.config.SHAREPOINT_TENANT_ID
    client_id = request.app.state.config.SHAREPOINT_CLIENT_ID
    client_secret = request.app.state.config.SHAREPOINT_CLIENT_SECRET

    cached = _sharepoint_token_cache.get("token")
    expires = float(_sharepoint_token_cache.get("expires", 0))
    if cached and time.time() < expires - 60:
        return str(cached)

    if not all([tenant_id, client_id, client_secret]):
        raise HTTPException(status_code=503, detail="SharePoint is not configured.")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=30,
        )
    response.raise_for_status()
    payload = response.json()
    _sharepoint_token_cache["token"] = payload["access_token"]
    _sharepoint_token_cache["expires"] = time.time() + payload.get("expires_in", 3600)
    return payload["access_token"]


async def _graph_get(request: Request, path: str, params: dict | None = None) -> dict:
    token = await _get_graph_token(request)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
            timeout=60,
        )
    response.raise_for_status()
    return response.json()


async def _get_site_id(request: Request, site_url: str) -> str:
    parsed = urlparse(site_url)
    data = await _graph_get(request, f"/sites/{parsed.netloc}:{parsed.path.rstrip('/')}")
    return data["id"]


async def _list_sharepoint_items(request: Request, site_id: str) -> list[dict]:
    data = await _graph_get(
        request, f"/sites/{site_id}/drive/root/children", params={"$top": 100}
    )
    return data.get("value", [])


async def _download_sharepoint_item(
    request: Request, site_id: str, item_id: str
) -> tuple[bytes, str, str | None]:
    metadata = await _graph_get(request, f"/sites/{site_id}/drive/items/{item_id}")
    download_url = metadata.get("@microsoft.graph.downloadUrl")
    if not download_url:
        return b"", "application/octet-stream", ""

    async with httpx.AsyncClient() as client:
        response = await client.get(download_url, timeout=60)
    response.raise_for_status()
    mime_type = (
        metadata.get("file", {}).get("mimeType")
        or response.headers.get("content-type")
        or "application/octet-stream"
    )
    text_content = None
    if mime_type.startswith("text/") or mime_type == "application/json":
        text_content = response.text
    return response.content, mime_type, text_content


async def _sync_sharepoint_site(
    request: Request,
    site_url: str,
    knowledge_base_id: str | None,
    access_control: dict | None,
) -> dict:
    user = get_integration_user()
    resolved_access_control = (
        access_control
        if access_control is not None
        else request.app.state.config.SHAREPOINT_ACCESS_CONTROL
    )
    knowledge_id = ensure_knowledge_base(
        user,
        knowledge_base_id or request.app.state.config.SHAREPOINT_KNOWLEDGE_ID or None,
        "SharePoint Sync",
        "Documents synchronized from SharePoint.",
        resolved_access_control,
    )

    site_id = await _get_site_id(request, site_url)
    items = await _list_sharepoint_items(request, site_id)
    synced = 0
    skipped = 0

    for item in items:
        if "file" not in item:
            skipped += 1
            continue

        content_bytes, content_type, text_content = await _download_sharepoint_item(
            request, site_id, item["id"]
        )
        upsert_external_file(
            request=request,
            user=user,
            knowledge_id=knowledge_id,
            source="sharepoint",
            external_id=item["id"],
            filename=item["name"],
            content_bytes=content_bytes,
            content_type=content_type,
            extra_meta={
                "site_url": site_url,
                "web_url": item.get("webUrl"),
                "modified_time": item.get("lastModifiedDateTime"),
            },
            process_content=text_content,
            access_control=resolved_access_control,
        )
        synced += 1

    return {
        "status": True,
        "source": "sharepoint",
        "knowledge_base_id": knowledge_id,
        "site_url": site_url,
        "access_control": resolved_access_control,
        "synced": synced,
        "skipped": skipped,
    }


@router.get("/api/v1/integrations/sources/config")
async def get_sources_config(request: Request, user=Depends(get_admin_user)):
    return _current_config(request)


@router.post("/api/v1/integrations/sources/config/update")
async def update_sources_config(
    request: Request,
    form_data: SourcesConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = form_data.gdrive.enabled
    request.app.state.config.GDRIVE_SERVICE_ACCOUNT_JSON = (
        form_data.gdrive.service_account_json
    )
    request.app.state.config.GDRIVE_WATCH_FOLDER_ID = form_data.gdrive.watch_folder_id
    request.app.state.config.GDRIVE_WEBHOOK_TOKEN = form_data.gdrive.webhook_token
    request.app.state.config.GDRIVE_KNOWLEDGE_ID = form_data.gdrive.knowledge_base_id
    request.app.state.config.GDRIVE_ACCESS_CONTROL = form_data.gdrive.access_control

    request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION = (
        form_data.sharepoint.enabled
    )
    request.app.state.config.SHAREPOINT_TENANT_ID = form_data.sharepoint.tenant_id
    request.app.state.config.SHAREPOINT_CLIENT_ID = form_data.sharepoint.client_id
    request.app.state.config.SHAREPOINT_CLIENT_SECRET = (
        form_data.sharepoint.client_secret
    )
    request.app.state.config.SHAREPOINT_SITE_URL = form_data.sharepoint.site_url
    request.app.state.config.SHAREPOINT_KNOWLEDGE_ID = (
        form_data.sharepoint.knowledge_base_id
    )
    request.app.state.config.SHAREPOINT_ACCESS_CONTROL = (
        form_data.sharepoint.access_control
    )

    return _current_config(request)


@router.post("/api/v1/integrations/gdrive/sync")
async def sync_gdrive(
    request: Request,
    body: GDriveSyncRequest,
    user=Depends(get_admin_user),
):
    folder_id = body.folder_id or request.app.state.config.GDRIVE_WATCH_FOLDER_ID
    if not folder_id:
        raise HTTPException(status_code=400, detail="No Google Drive folder configured.")
    return await _sync_gdrive_folder(
        request,
        folder_id,
        body.knowledge_base_id,
        body.access_control,
    )


@router.post("/api/v1/integrations/gdrive/webhook")
async def gdrive_webhook(
    request: Request,
    x_goog_channel_token: str = Header(default=""),
    x_goog_resource_state: str = Header(default=""),
):
    webhook_token = request.app.state.config.GDRIVE_WEBHOOK_TOKEN
    folder_id = request.app.state.config.GDRIVE_WATCH_FOLDER_ID

    if webhook_token and x_goog_channel_token != webhook_token:
        raise HTTPException(status_code=403, detail="Invalid webhook token.")

    if x_goog_resource_state == "sync":
        return JSONResponse({"ok": True})

    if folder_id:
        asyncio.create_task(_sync_gdrive_folder(request, folder_id, None, None))
    return JSONResponse({"ok": True})


@router.get("/api/v1/integrations/gdrive/files")
async def list_gdrive_files(user=Depends(get_admin_user)):
    files = _get_source_files("gdrive")
    return {"count": len(files), "files": files}


@router.delete("/api/v1/integrations/gdrive/files")
async def delete_gdrive_files(user=Depends(get_admin_user)):
    deleted = _delete_source_files("gdrive")
    return {"status": True, "source": "gdrive", "deleted": deleted}


@router.post("/api/v1/integrations/sharepoint/sync")
async def sync_sharepoint(
    request: Request,
    body: SharePointSyncRequest,
    user=Depends(get_admin_user),
):
    site_url = body.site_url or request.app.state.config.SHAREPOINT_SITE_URL
    if not site_url:
        raise HTTPException(status_code=400, detail="No SharePoint site configured.")
    return await _sync_sharepoint_site(
        request,
        site_url,
        body.knowledge_base_id,
        body.access_control,
    )


@router.get("/api/v1/integrations/sharepoint/files")
async def list_sharepoint_files(user=Depends(get_admin_user)):
    files = _get_source_files("sharepoint")
    return {"count": len(files), "files": files}


@router.delete("/api/v1/integrations/sharepoint/files")
async def delete_sharepoint_files(user=Depends(get_admin_user)):
    deleted = _delete_source_files("sharepoint")
    return {"status": True, "source": "sharepoint", "deleted": deleted}


@router.get("/api/v1/integrations/sharepoint/sites")
async def list_sharepoint_sites(request: Request, user=Depends(get_admin_user)):
    data = await _graph_get(request, "/sites", params={"search": "*", "$top": 20})
    return {
        "sites": [
            {
                "id": site["id"],
                "name": site.get("displayName", ""),
                "url": site.get("webUrl", ""),
            }
            for site in data.get("value", [])
        ]
    }


@router.get("/api/v1/integrations/sources/health")
async def external_sources_health(request: Request):
    return {
        "status": True,
        "gdrive_configured": bool(
            request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION
            and request.app.state.config.GDRIVE_SERVICE_ACCOUNT_JSON
            and request.app.state.config.GDRIVE_WATCH_FOLDER_ID
        ),
        "sharepoint_configured": bool(
            request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION
            and request.app.state.config.SHAREPOINT_TENANT_ID
            and request.app.state.config.SHAREPOINT_CLIENT_ID
            and request.app.state.config.SHAREPOINT_CLIENT_SECRET
        ),
    }
