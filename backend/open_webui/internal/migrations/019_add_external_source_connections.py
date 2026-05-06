"""Peewee migrations -- 019_add_external_source_connections.py."""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    @migrator.create_model
    class ExternalSourceConnection(pw.Model):
        id = pw.TextField(primary_key=True, unique=True)
        provider = pw.CharField(max_length=255)
        user_id = pw.TextField()
        oauth_session_id = pw.TextField(null=True)
        display_name = pw.TextField()
        account_email = pw.TextField(null=True)
        status = pw.CharField(max_length=255, default="connected")
        knowledge_base_id = pw.TextField(null=True)
        access_control = pw.TextField(null=True)
        config = pw.TextField(null=True)
        last_synced_at = pw.BigIntegerField(null=True)
        created_at = pw.BigIntegerField(null=False)
        updated_at = pw.BigIntegerField(null=False)

        class Meta:
            table_name = "external_source_connection"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    migrator.remove_model("external_source_connection")
