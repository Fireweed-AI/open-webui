from open_webui.utils.external_sources.base import ExternalSourceProvider
from open_webui.utils.external_sources.google_drive import GoogleDriveProvider


PROVIDERS: dict[str, ExternalSourceProvider] = {
    GoogleDriveProvider.id: GoogleDriveProvider(),
}


def list_external_source_providers() -> list[ExternalSourceProvider]:
    return list(PROVIDERS.values())


def get_external_source_provider(provider_id: str) -> ExternalSourceProvider | None:
    return PROVIDERS.get(provider_id)


def get_provider_for_connection_provider(connection_provider: str) -> ExternalSourceProvider | None:
    for provider in PROVIDERS.values():
        if provider.connection_provider == connection_provider:
            return provider
    return None
