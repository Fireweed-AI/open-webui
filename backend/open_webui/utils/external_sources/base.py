from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fastapi import Request

from open_webui.models.external_source_connections import (
    ExternalSourceConnectionModel,
)


class ExternalSourceProvider(ABC):
    id: str
    connection_provider: str
    name: str
    description: str
    icon: str
    selection_label: str
    empty_selection_message: str
    sync_success_label: str
    synced_files_label: str
    no_files_message: str
    callback_query_key: str

    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "connection_provider": self.connection_provider,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "selection_label": self.selection_label,
            "empty_selection_message": self.empty_selection_message,
            "sync_success_label": self.sync_success_label,
            "synced_files_label": self.synced_files_label,
            "no_files_message": self.no_files_message,
            "callback_query_key": self.callback_query_key,
        }

    @abstractmethod
    def get_default_connection_config(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def serialize_connection(self, connection: ExternalSourceConnectionModel) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def build_authorize_url(
        self, request: Request, user_id: str, next_path: str
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def complete_connection_callback(
        self, request: Request, code: str, state: str
    ) -> tuple[ExternalSourceConnectionModel, str]:
        raise NotImplementedError

    @abstractmethod
    async def update_connection(
        self,
        request: Request,
        connection: ExternalSourceConnectionModel,
        payload: dict[str, Any],
    ) -> ExternalSourceConnectionModel:
        raise NotImplementedError

    @abstractmethod
    async def get_selection_token(
        self, request: Request, connection: ExternalSourceConnectionModel
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def sync_connection(
        self, request: Request, connection: ExternalSourceConnectionModel
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def preview_selection(
        self, request: Request, connection: ExternalSourceConnectionModel
    ) -> dict[str, Any]:
        raise NotImplementedError
