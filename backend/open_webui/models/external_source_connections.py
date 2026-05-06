import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, JSON, String, Text

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class ExternalSourceConnection(Base):
    __tablename__ = "external_source_connection"

    id = Column(Text, primary_key=True, unique=True)
    provider = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    oauth_session_id = Column(Text, nullable=True)

    display_name = Column(Text, nullable=False)
    account_email = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="connected")

    knowledge_base_id = Column(Text, nullable=True)
    access_control = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)

    last_synced_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class ExternalSourceConnectionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    user_id: str
    oauth_session_id: Optional[str] = None

    display_name: str
    account_email: Optional[str] = None
    status: str

    knowledge_base_id: Optional[str] = None
    access_control: Optional[dict] = None
    config: Optional[dict] = None

    last_synced_at: Optional[int] = None
    created_at: int
    updated_at: int


class ExternalSourceConnectionForm(BaseModel):
    provider: str
    display_name: str
    account_email: Optional[str] = None
    oauth_session_id: Optional[str] = None
    status: str = "connected"
    knowledge_base_id: Optional[str] = None
    access_control: Optional[dict] = None
    config: Optional[dict] = None
    last_synced_at: Optional[int] = None


class ExternalSourceConnectionUpdateForm(BaseModel):
    display_name: Optional[str] = None
    account_email: Optional[str] = None
    oauth_session_id: Optional[str] = None
    status: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    access_control: Optional[dict] = None
    config: Optional[dict] = None
    last_synced_at: Optional[int] = None


class ExternalSourceConnectionsTable:
    def insert_new_connection(
        self, user_id: str, form_data: ExternalSourceConnectionForm
    ) -> Optional[ExternalSourceConnectionModel]:
        with get_db() as db:
            connection = ExternalSourceConnectionModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=int(time.time()),
                updated_at=int(time.time()),
                **form_data.model_dump(),
            )

            try:
                result = ExternalSourceConnection(**connection.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return ExternalSourceConnectionModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting external source connection: {e}")
                return None

    def get_connection_by_id(self, id: str) -> Optional[ExternalSourceConnectionModel]:
        with get_db() as db:
            try:
                result = db.query(ExternalSourceConnection).filter_by(id=id).first()
                return (
                    ExternalSourceConnectionModel.model_validate(result)
                    if result
                    else None
                )
            except Exception:
                return None

    def get_connections(
        self, provider: Optional[str] = None, user_id: Optional[str] = None
    ) -> list[ExternalSourceConnectionModel]:
        with get_db() as db:
            query = db.query(ExternalSourceConnection)
            if provider:
                query = query.filter_by(provider=provider)
            if user_id:
                query = query.filter_by(user_id=user_id)

            query = query.order_by(
                ExternalSourceConnection.updated_at.desc(),
                ExternalSourceConnection.created_at.desc(),
            )
            return [
                ExternalSourceConnectionModel.model_validate(item)
                for item in query.all()
            ]

    def update_connection_by_id(
        self, id: str, form_data: ExternalSourceConnectionUpdateForm
    ) -> Optional[ExternalSourceConnectionModel]:
        with get_db() as db:
            try:
                payload = {
                    key: value
                    for key, value in form_data.model_dump().items()
                    if key in form_data.model_fields_set
                }
                payload["updated_at"] = int(time.time())

                db.query(ExternalSourceConnection).filter_by(id=id).update(payload)
                db.commit()

                result = db.query(ExternalSourceConnection).filter_by(id=id).first()
                return (
                    ExternalSourceConnectionModel.model_validate(result)
                    if result
                    else None
                )
            except Exception as e:
                log.exception(f"Error updating external source connection: {e}")
                return None

    def delete_connection_by_id(self, id: str) -> bool:
        with get_db() as db:
            try:
                result = db.query(ExternalSourceConnection).filter_by(id=id).delete()
                db.commit()
                return result > 0
            except Exception as e:
                log.exception(f"Error deleting external source connection: {e}")
                return False


ExternalSourceConnections = ExternalSourceConnectionsTable()
