import json
import time
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request

from open_webui.models.external_source_connections import (
    ExternalSourceConnectionForm,
    ExternalSourceConnectionModel,
    ExternalSourceConnections,
    ExternalSourceConnectionUpdateForm,
)
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.users import Users
from open_webui.utils.auth import create_token, decode_token
from open_webui.utils.external_sources.base import ExternalSourceProvider
from open_webui.utils.source_sync import (
    ensure_external_file_in_knowledge,
    ensure_knowledge_base,
    get_existing_external_file,
    upsert_external_file,
)


GOOGLE_DRIVE_OAUTH_PROVIDER = "google_drive_connection"
GOOGLE_DRIVE_PROVIDER_ID = "google-drive"
GOOGLE_DRIVE_CONNECTION_PROVIDER = "gdrive"
GOOGLE_DRIVE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_google_drive_client_id(request: Request) -> str:
    client_id = str(request.app.state.config.GOOGLE_DRIVE_CLIENT_ID)
    if not client_id:
        raise HTTPException(status_code=503, detail="Google Drive client ID is not configured.")
    return client_id


def _get_google_drive_client_secret(request: Request) -> str:
    client_secret = str(request.app.state.config.GOOGLE_DRIVE_CLIENT_SECRET)
    if not client_secret:
        raise HTTPException(
            status_code=503, detail="Google Drive client secret is not configured."
        )
    return client_secret


def get_google_drive_callback_url(request: Request) -> str:
    return str(
        request.url_for(
            "source_connection_provider_callback", provider=GOOGLE_DRIVE_PROVIDER_ID
        )
    )


def create_google_drive_connect_state(user_id: str, next_path: str) -> str:
    return create_token(
        {
            "id": user_id,
            "purpose": "google_drive_connection",
            "next_path": next_path,
        },
        expires_delta=timedelta(minutes=10),
    )


def parse_google_drive_connect_state(state: str) -> dict:
    payload = decode_token(state)
    if payload is None or payload.get("purpose") != "google_drive_connection":
        raise HTTPException(status_code=400, detail="Invalid Google Drive connection state.")
    return payload


def build_google_drive_authorize_url(request: Request, user_id: str, next_path: str) -> str:
    params = {
        "client_id": _get_google_drive_client_id(request),
        "redirect_uri": get_google_drive_callback_url(request),
        "response_type": "code",
        "scope": " ".join(GOOGLE_DRIVE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": create_google_drive_connect_state(user_id, next_path),
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_google_drive_code(request: Request, code: str) -> dict:
    payload = {
        "code": code,
        "client_id": _get_google_drive_client_id(request),
        "client_secret": _get_google_drive_client_secret(request),
        "redirect_uri": get_google_drive_callback_url(request),
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data=payload,
            timeout=30,
        )

    if not response.is_success:
        raise HTTPException(status_code=400, detail="Failed to exchange Google Drive code.")

    token = response.json()
    token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600))
    return token


async def refresh_google_drive_token(request: Request, oauth_session_id: str) -> dict:
    session = OAuthSessions.get_session_by_id(oauth_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Google Drive OAuth session not found.")

    token = session.token
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Google Drive refresh token is missing.")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": _get_google_drive_client_id(request),
                "client_secret": _get_google_drive_client_secret(request),
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

    if not response.is_success:
        raise HTTPException(status_code=400, detail="Failed to refresh Google Drive token.")

    refreshed = response.json()
    merged_token = {
        **token,
        **refreshed,
        "refresh_token": token.get("refresh_token"),
        "expires_at": int(time.time()) + int(refreshed.get("expires_in", 3600)),
    }

    updated = OAuthSessions.update_session_by_id(oauth_session_id, merged_token)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to persist refreshed Google Drive token.")
    return updated.token


async def get_google_drive_access_token(
    request: Request, connection: ExternalSourceConnectionModel
) -> str:
    if not connection.oauth_session_id:
        raise HTTPException(status_code=400, detail="Google Drive connection is missing OAuth credentials.")

    session = OAuthSessions.get_session_by_id(connection.oauth_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Google Drive OAuth session not found.")

    token = session.token
    if int(token.get("expires_at", 0)) <= int(time.time()) + 60:
        token = await refresh_google_drive_token(request, connection.oauth_session_id)

    access_token = token.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Google Drive access token is unavailable.")

    return str(access_token)


async def get_google_drive_account_profile(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

    if not response.is_success:
        raise HTTPException(status_code=400, detail="Failed to fetch Google Drive account profile.")
    return response.json()


async def list_google_drive_files(
    access_token: str, folder_id: str, mime_type_filter: str | None = None
) -> list[dict]:
    query = [f"'{folder_id}' in parents", "trashed = false"]
    if mime_type_filter:
        query.append(f"mimeType = '{mime_type_filter}'")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "q": " and ".join(query),
                "fields": "files(id,name,mimeType,modifiedTime,size,parents)",
                "pageSize": 100,
                "includeItemsFromAllDrives": "true",
                "supportsAllDrives": "true",
            },
            timeout=30,
        )

    if not response.is_success:
        raise HTTPException(status_code=400, detail="Failed to list Google Drive files.")
    return response.json().get("files", [])


async def list_google_drive_files_recursive(
    access_token: str, folder_id: str
) -> tuple[list[dict], int]:
    queue = [folder_id]
    files: list[dict] = []
    traversed_folders = 0

    while queue:
        current_folder_id = queue.pop(0)
        items = await list_google_drive_files(access_token, current_folder_id)
        for item in items:
            mime_type = item.get("mimeType", "")
            if mime_type.startswith("application/vnd.google-apps.folder"):
                queue.append(item["id"])
                traversed_folders += 1
                continue
            files.append(item)

    return files, traversed_folders


async def preview_google_drive_connection(
    request: Request, connection: ExternalSourceConnectionModel
) -> dict:
    folders = _get_connection_folders(connection)
    if not folders:
        return {"status": True, "folders": [], "total_files": 0, "truncated": False}

    access_token = await get_google_drive_access_token(request, connection)
    preview_limit = 100
    remaining = preview_limit
    total_files = 0
    truncated = False
    preview_folders = []

    for folder in folders:
        folder_id = folder.get("id")
        folder_name = folder.get("name", folder_id)
        if not folder_id:
            continue

        files, traversed_folders = await list_google_drive_files_recursive(access_token, folder_id)
        total_files += len(files)

        folder_preview = []
        if remaining > 0:
            folder_preview = [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "mime_type": item.get("mimeType"),
                    "modified_time": item.get("modifiedTime"),
                }
                for item in files[:remaining]
            ]
            remaining -= len(folder_preview)

        if len(files) > len(folder_preview):
            truncated = True

        preview_folders.append(
            {
                "id": folder_id,
                "name": folder_name,
                "file_count": len(files),
                "traversed_folders": traversed_folders,
                "files": folder_preview,
            }
        )

    if total_files > preview_limit:
        truncated = True

    return {
        "status": True,
        "folders": preview_folders,
        "total_files": total_files,
        "truncated": truncated,
    }


async def download_google_drive_file(
    access_token: str, file_id: str, mime_type: str
) -> tuple[bytes, str, str | None]:
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
                headers={"Authorization": f"Bearer {access_token}"},
                params={"mimeType": export_type},
                timeout=60,
            )
            if not response.is_success:
                raise HTTPException(status_code=400, detail="Failed to export Google Drive file.")
            return response.content, export_type, response.text

        response = await client.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )

    if not response.is_success:
        raise HTTPException(status_code=400, detail="Failed to download Google Drive file.")

    text_content = None
    if mime_type.startswith("text/") or mime_type == "application/json":
        text_content = response.text

    return response.content, mime_type or "application/octet-stream", text_content


def _get_connection_folders(connection: ExternalSourceConnectionModel) -> list[dict]:
    config = connection.config or {}
    folders = config.get("folders", [])
    return folders if isinstance(folders, list) else []


def _get_synced_google_drive_filename(file_name: str, mime_type: str) -> str:
    if mime_type == "application/vnd.google-apps.document":
        return f"{file_name}.txt"
    if mime_type == "application/vnd.google-apps.spreadsheet":
        return f"{file_name}.csv"
    if mime_type == "application/vnd.google-apps.presentation":
        return f"{file_name}.txt"
    return file_name


async def sync_google_drive_connection(
    request: Request, connection: ExternalSourceConnectionModel
) -> dict:
    owner = Users.get_user_by_id(connection.user_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Connection owner not found.")

    folders = _get_connection_folders(connection)
    if not folders:
        raise HTTPException(status_code=400, detail="No Google Drive folders selected.")

    access_token = await get_google_drive_access_token(request, connection)

    knowledge_id = ensure_knowledge_base(
        owner,
        connection.knowledge_base_id or None,
        connection.display_name,
        f"Documents synchronized from {connection.display_name}.",
        connection.access_control,
    )

    synced = 0
    skipped = 0
    unchanged = 0
    for folder in folders:
        folder_id = folder.get("id")
        folder_name = folder.get("name", folder_id)
        if not folder_id:
            continue

        files, traversed_folders = await list_google_drive_files_recursive(
            access_token, folder_id
        )
        skipped += traversed_folders
        for file in files:
            mime_type = file.get("mimeType", "")
            filename = _get_synced_google_drive_filename(file["name"], mime_type)
            existing = get_existing_external_file("gdrive", file["id"], connection.id)
            existing_meta = ((existing.meta or {}).get("data") or {}) if existing else {}

            if (
                existing is not None
                and existing_meta.get("modified_time") == file.get("modifiedTime")
                and existing_meta.get("folder_id") == folder_id
                and existing_meta.get("folder_name") == folder_name
                and existing_meta.get("parents", []) == file.get("parents", [])
                and existing.filename == filename
                and existing.access_control == connection.access_control
            ):
                ensure_external_file_in_knowledge(knowledge_id, existing.id, owner.id)
                unchanged += 1
                continue

            content_bytes, content_type, text_content = await download_google_drive_file(
                access_token, file["id"], mime_type
            )

            upsert_external_file(
                request=request,
                user=owner,
                knowledge_id=knowledge_id,
                source="gdrive",
                source_connection_id=connection.id,
                source_provider_id=GOOGLE_DRIVE_PROVIDER_ID,
                external_id=file["id"],
                filename=filename,
                content_bytes=content_bytes,
                content_type=content_type,
                extra_meta={
                    "folder_id": folder_id,
                    "folder_name": folder_name,
                    "modified_time": file.get("modifiedTime"),
                    "parents": file.get("parents", []),
                },
                process_content=text_content,
                access_control=connection.access_control,
            )
            synced += 1

    updated = ExternalSourceConnections.update_connection_by_id(
        connection.id,
        ExternalSourceConnectionUpdateForm(
            knowledge_base_id=knowledge_id,
            last_synced_at=int(time.time()),
            status="connected",
        ),
    )

    return {
        "status": True,
        "provider": connection.provider,
        "connection_id": connection.id,
        "knowledge_base_id": knowledge_id,
        "folders": folders,
        "synced": synced,
        "unchanged": unchanged,
        "skipped": skipped,
        "last_synced_at": updated.last_synced_at if updated else int(time.time()),
    }


class GoogleDriveProvider(ExternalSourceProvider):
    id = GOOGLE_DRIVE_PROVIDER_ID
    connection_provider = GOOGLE_DRIVE_CONNECTION_PROVIDER
    name = "Google Drive"
    description = "Connect a Google account, choose folders, and sync them into Fireweed knowledge."
    icon = "google-drive"
    selection_label = "Selected Folders"
    empty_selection_message = "No folders selected yet."
    sync_success_label = "Synced {{count}} Google Drive files"
    synced_files_label = "Synced Files"
    no_files_message = "No Google Drive files have been synced yet."
    callback_query_key = "connection_added"

    def get_default_connection_config(self) -> dict:
        return {"folders": []}

    def serialize_connection(self, connection: ExternalSourceConnectionModel) -> dict:
        payload = connection.model_dump()
        config = payload.get("config") or {}
        payload["selected_resources"] = config.get("folders", [])
        payload["provider_id"] = self.id
        return payload

    async def build_authorize_url(
        self, request: Request, user_id: str, next_path: str
    ) -> str:
        return build_google_drive_authorize_url(request, user_id, next_path)

    async def complete_connection_callback(
        self, request: Request, code: str, state: str
    ) -> tuple[ExternalSourceConnectionModel, str]:
        state_payload = parse_google_drive_connect_state(state)
        user_id = state_payload["id"]

        token = await exchange_google_drive_code(request, code)
        session = OAuthSessions.create_session(
            user_id, GOOGLE_DRIVE_OAUTH_PROVIDER, token
        )
        if session is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to store Google Drive OAuth session.",
            )

        access_token = token.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400, detail="Missing Google Drive access token."
            )

        profile = await get_google_drive_account_profile(str(access_token))
        display_name = profile.get("name") or profile.get("email") or "Google Drive"

        connection = ExternalSourceConnections.insert_new_connection(
            user_id,
            ExternalSourceConnectionForm(
                provider=self.connection_provider,
                display_name=f"{display_name} Drive",
                account_email=profile.get("email"),
                oauth_session_id=session.id,
                access_control={},
                config=self.get_default_connection_config(),
            ),
        )
        if connection is None:
            raise HTTPException(
                status_code=500, detail="Failed to create Google Drive connection."
            )

        next_path = state_payload.get("next_path") or "/admin/settings/documents"
        return connection, next_path

    async def update_connection(
        self,
        request: Request,
        connection: ExternalSourceConnectionModel,
        payload: dict,
    ) -> ExternalSourceConnectionModel:
        config = connection.config or {}
        selected_resources = payload.get("selected_resources") or []
        config["folders"] = selected_resources

        updated = ExternalSourceConnections.update_connection_by_id(
            connection.id,
            ExternalSourceConnectionUpdateForm(
                display_name=payload.get("display_name") or connection.display_name,
                knowledge_base_id=payload.get("knowledge_base_id"),
                access_control=payload.get("access_control"),
                config=config,
            ),
        )
        if updated is None:
            raise HTTPException(status_code=500, detail="Failed to update connection.")
        return updated

    async def get_selection_token(
        self, request: Request, connection: ExternalSourceConnectionModel
    ) -> dict:
        access_token = await get_google_drive_access_token(request, connection)
        expires_at = int(time.time()) + 300
        return {"access_token": access_token, "expires_at": expires_at}

    async def sync_connection(
        self, request: Request, connection: ExternalSourceConnectionModel
    ) -> dict:
        return await sync_google_drive_connection(request, connection)

    async def preview_selection(
        self, request: Request, connection: ExternalSourceConnectionModel
    ) -> dict:
        return await preview_google_drive_connection(request, connection)
