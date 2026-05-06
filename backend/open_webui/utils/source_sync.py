import io
import logging
import os
import uuid
from typing import Any

from fastapi import HTTPException, Request

from open_webui.models.files import FileForm, Files
from open_webui.models.knowledge import KnowledgeForm, Knowledges
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.storage.provider import Storage
from open_webui.utils.misc import calculate_sha256_string
from open_webui.models.users import UserModel


log = logging.getLogger(__name__)


def ensure_knowledge_base(
    user: UserModel,
    knowledge_id: str | None,
    fallback_name: str,
    description: str,
    access_control: dict | None,
) -> str:
    if knowledge_id:
        knowledge = Knowledges.get_knowledge_by_id(knowledge_id)
        if knowledge is None:
            raise HTTPException(status_code=404, detail="Knowledge base not found.")
        if access_control is not None and knowledge.access_control != access_control:
            Knowledges.update_knowledge_by_id(
                knowledge.id,
                KnowledgeForm(
                    name=knowledge.name,
                    description=knowledge.description,
                    access_control=access_control,
                ),
            )
        return knowledge.id

    for knowledge in Knowledges.get_knowledge_bases():
        if knowledge.user_id == user.id and knowledge.name == fallback_name:
            if access_control is not None and knowledge.access_control != access_control:
                Knowledges.update_knowledge_by_id(
                    knowledge.id,
                    KnowledgeForm(
                        name=knowledge.name,
                        description=knowledge.description,
                        access_control=access_control,
                    ),
                )
            return knowledge.id

    created = Knowledges.insert_new_knowledge(
        user.id,
        KnowledgeForm(
            name=fallback_name,
            description=description,
            access_control=access_control,
        ),
    )
    if created is None:
        raise HTTPException(status_code=500, detail="Failed to create knowledge base.")
    return created.id


def _find_existing_external_file(
    source: str, external_id: str, source_connection_id: str | None = None
):
    for file in Files.get_files():
        meta_data = ((file.meta or {}).get("data") or {})
        if meta_data.get("external_source") != source:
            continue
        if source_connection_id is not None and (
            meta_data.get("external_source_connection_id") != source_connection_id
        ):
            continue
        if meta_data.get("external_id") == external_id:
            return file
    return None


def get_existing_external_file(
    source: str, external_id: str, source_connection_id: str | None = None
):
    return _find_existing_external_file(source, external_id, source_connection_id)


def ensure_external_file_in_knowledge(
    knowledge_id: str, file_id: str, user_id: str
) -> None:
    existing_knowledge_ids = {
        knowledge.id for knowledge in Knowledges.get_knowledges_by_file_id(file_id)
    }
    if knowledge_id not in existing_knowledge_ids:
        Knowledges.add_file_to_knowledge_by_id(knowledge_id, file_id, user_id)


def upsert_external_file(
    request: Request,
    user: UserModel,
    knowledge_id: str,
    source: str,
    external_id: str,
    filename: str,
    content_bytes: bytes,
    content_type: str,
    extra_meta: dict[str, Any] | None = None,
    process_content: str | None = None,
    access_control: dict | None = None,
    source_connection_id: str | None = None,
    source_provider_id: str | None = None,
) -> str:
    existing = _find_existing_external_file(source, external_id, source_connection_id)
    if existing is not None:
        for knowledge in Knowledges.get_knowledges_by_file_id(existing.id):
            Knowledges.remove_file_from_knowledge_by_id(knowledge.id, existing.id)
        if existing.path:
            try:
                Storage.delete_file(existing.path)
            except Exception:
                log.exception("Failed to delete prior synced file from storage")
        Files.delete_file_by_id(existing.id)

    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}_{os.path.basename(filename)}"
    _, file_path = Storage.upload_file(
        io.BytesIO(content_bytes),
        stored_name,
        {
            "OpenWebUI-User-Email": user.email,
            "OpenWebUI-User-Id": user.id,
            "OpenWebUI-User-Name": user.name,
            "OpenWebUI-File-Id": file_id,
        },
    )

    file_item = Files.insert_new_file(
        user.id,
        FileForm(
            id=file_id,
            filename=os.path.basename(filename),
            path=file_path,
            data={"status": "pending"},
            meta={
                "name": os.path.basename(filename),
                "content_type": content_type,
                "size": len(content_bytes),
                "collection_name": knowledge_id,
                "data": {
                    "external_source": source,
                    "external_source_provider_id": source_provider_id or source,
                    "external_source_connection_id": source_connection_id,
                    "external_id": external_id,
                    **(extra_meta or {}),
                },
            },
            access_control=access_control,
        ),
    )
    if file_item is None:
        raise HTTPException(status_code=500, detail="Failed to store synced file.")

    if process_content is not None:
        Files.update_file_hash_by_id(file_id, calculate_sha256_string(process_content))
        process_file(
            request,
            ProcessFileForm(
                file_id=file_id,
                content=process_content,
                collection_name=knowledge_id,
            ),
            user=user,
        )
    else:
        process_file(
            request,
            ProcessFileForm(file_id=file_id, collection_name=knowledge_id),
            user=user,
        )

    Knowledges.add_file_to_knowledge_by_id(knowledge_id, file_id, user.id)
    return file_id
