<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		deleteSourceConnection,
		deleteSourceConnectionFiles,
		getProviderConnectUrl,
		getSourceConnectionFiles,
		getSourceConnections,
		getSourceConnectionSelectionToken,
		getSourceProviders,
		previewSourceConnection,
		syncSourceConnection,
		updateSourceConnection
	} from '$lib/apis/integrations';
	import ExternalSourcesConnectionDetail from '$lib/components/admin/Settings/Documents/ExternalSourcesConnectionDetail.svelte';
	import ExternalSourcesLanding from '$lib/components/admin/Settings/Documents/ExternalSourcesLanding.svelte';
	import ExternalSourcesSidebar from '$lib/components/admin/Settings/Documents/ExternalSourcesSidebar.svelte';
	import { createGoogleDriveFolderPicker } from '$lib/utils/google-drive-folder-picker';

	const i18n = getContext('i18n');
	const LAST_PROVIDER_STORAGE_KEY = 'external-sources:selected-provider';

	export let knowledgeBases = [];

	let providers = [];
	let selectedProviderId = '';
	let selectedProvider = null;

	let connections = [];
	let selectedConnectionId = '';
	let selectedConnection = null;
	let connectionFiles = [];

	let providersLoading = false;
	let connectionsLoading = false;
	let filesLoading = false;
	let previewLoading = false;
	let syncLoading = false;
	let selectionLoading = false;
	let savingConnection = false;
	let deletingConnection = false;
	let deletingFiles = false;

	let knowledgeBaseId = '';
	let accessControl = {};
	let selectedResources = [];
	let selectionPreview = null;

	const getError = (error: any) => `${error?.detail || error?.message || error}`;

	const selectionLabel = () => selectedProvider?.selection_label || $i18n.t('Selected Resources');
	const emptySelectionMessage = () =>
		selectedProvider?.empty_selection_message || $i18n.t('No resources selected yet.');
	const syncedFilesLabel = () => selectedProvider?.synced_files_label || $i18n.t('Synced Files');
	const noFilesMessage = () =>
		selectedProvider?.no_files_message || $i18n.t('No synced files yet.');
	const previewHeading = () =>
		selectedProviderId === 'google-drive'
			? $i18n.t('Selected Folder Contents')
			: $i18n.t('Selected Resource Contents');

	const getSelectionActionLabel = () => {
		if (selectedProviderId === 'google-drive') {
			return $i18n.t('Select Folders');
		}
		return $i18n.t('Select Resources');
	};

	const getConnectLabel = () => {
		if (selectedProvider) {
			return $i18n.t('Connect {{provider}}', { provider: selectedProvider.name });
		}
		return $i18n.t('Connect');
	};

	const selectConnection = async (connectionId: string) => {
		selectedConnectionId = connectionId;
		selectedConnection =
			connections.find((connection) => connection.id === connectionId) ?? null;
		knowledgeBaseId = selectedConnection?.knowledge_base_id ?? '';
		accessControl = selectedConnection?.access_control ?? {};
		selectedResources = selectedConnection?.selected_resources ?? [];
		await refreshSelectionPreview();
		await refreshConnectionFiles();
	};

	const resetSelectedConnection = () => {
		selectedConnectionId = '';
		selectedConnection = null;
		connectionFiles = [];
		knowledgeBaseId = '';
		accessControl = {};
		selectedResources = [];
		selectionPreview = null;
	};

	const refreshSelectionPreview = async () => {
		if (!selectedConnectionId) {
			selectionPreview = null;
			return;
		}

		previewLoading = true;
		const res = await previewSourceConnection(localStorage.token, selectedConnectionId).catch(
			(error) => {
				toast.error(getError(error));
				return null;
			}
		);
		previewLoading = false;

		if (res) {
			selectionPreview = res;
		}
	};

	const refreshConnections = async () => {
		if (!selectedProviderId) {
			connections = [];
			resetSelectedConnection();
			return;
		}

		connectionsLoading = true;
		const res = await getSourceConnections(localStorage.token, selectedProviderId).catch((error) => {
			toast.error(getError(error));
			return null;
		});
		connectionsLoading = false;

		if (!res) {
			return;
		}

		connections = res.connections ?? [];

		if (selectedConnectionId) {
			const nextSelected =
				connections.find((connection) => connection.id === selectedConnectionId)?.id ?? '';
			if (nextSelected) {
				await selectConnection(nextSelected);
				return;
			}
		}

		if (connections.length > 0) {
			await selectConnection(connections[0].id);
			return;
		}

		resetSelectedConnection();
	};

	const selectProvider = async (providerId: string) => {
		selectedProviderId = providerId;
		selectedProvider = providers.find((provider) => provider.id === providerId) ?? null;
		sessionStorage.setItem(LAST_PROVIDER_STORAGE_KEY, providerId);
		resetSelectedConnection();
		await refreshConnections();
	};

	const returnToProviders = () => {
		sessionStorage.removeItem(LAST_PROVIDER_STORAGE_KEY);
		selectedProviderId = '';
		selectedProvider = null;
		connections = [];
		resetSelectedConnection();
	};

	const refreshProviders = async () => {
		providersLoading = true;
		const res = await getSourceProviders(localStorage.token).catch((error) => {
			toast.error(getError(error));
			return null;
		});
		providersLoading = false;

		if (!res) {
			return;
		}

		providers = res.providers ?? [];

		if (selectedProviderId && providers.some((provider) => provider.id === selectedProviderId)) {
			await selectProvider(selectedProviderId);
			return;
		}

		selectedProvider = null;
		connections = [];
		resetSelectedConnection();
	};

	const refreshConnectionFiles = async () => {
		if (!selectedConnectionId) {
			connectionFiles = [];
			return;
		}

		filesLoading = true;
		const res = await getSourceConnectionFiles(localStorage.token, selectedConnectionId).catch(
			(error) => {
				toast.error(getError(error));
				return null;
			}
		);
		filesLoading = false;

		if (res) {
			connectionFiles = res.files ?? [];
		}
	};

	const connectProvider = async () => {
		if (!selectedProviderId) {
			return;
		}

		const nextPath = `${window.location.origin}/admin/settings/documents`;

		const res = await getProviderConnectUrl(
			localStorage.token,
			selectedProviderId,
			nextPath
		).catch((error) => {
			toast.error(getError(error));
			return null;
		});

		if (res?.authorize_url) {
			window.location.href = res.authorize_url;
		}
	};

	const saveConnection = async () => {
		if (!selectedConnectionId) {
			return;
		}

		savingConnection = true;
		const res = await updateSourceConnection(localStorage.token, selectedConnectionId, {
			knowledge_base_id: knowledgeBaseId || null,
			access_control: accessControl,
			selected_resources: selectedResources
		}).catch((error) => {
			toast.error(getError(error));
			return null;
		});
		savingConnection = false;

		if (res) {
			selectedConnection = res;
			toast.success($i18n.t('Settings saved successfully!'));
			await refreshConnections();
			await refreshSelectionPreview();
		}
	};

	const pickResources = async () => {
		if (!selectedConnectionId || !selectedProviderId) {
			return;
		}

		selectionLoading = true;
		const tokenRes = await getSourceConnectionSelectionToken(
			localStorage.token,
			selectedConnectionId
		).catch((error) => {
			toast.error(getError(error));
			return null;
		});

		if (!tokenRes?.access_token) {
			selectionLoading = false;
			return;
		}

		let pickedResources = null;
		if (selectedProviderId === 'google-drive') {
			pickedResources = await createGoogleDriveFolderPicker(tokenRes.access_token).catch((error) => {
				toast.error(getError(error));
				return null;
			});
		} else {
			toast.error($i18n.t('Resource picker not implemented for this provider yet.'));
		}

		selectionLoading = false;

		if (!pickedResources || pickedResources.length === 0) {
			return;
		}

		const resourceMap = new Map(selectedResources.map((resource) => [resource.id, resource]));
		for (const resource of pickedResources as any[]) {
			resourceMap.set(resource.id, resource);
		}
		selectedResources = Array.from(resourceMap.values());
		await saveConnection();
	};

	const removeResource = async (resourceId: string) => {
		selectedResources = selectedResources.filter((resource) => resource.id !== resourceId);
		await saveConnection();
	};

	const syncSelectedConnection = async () => {
		if (!selectedConnectionId) {
			return;
		}

		await saveConnection();

		syncLoading = true;
		const res = await syncSourceConnection(localStorage.token, selectedConnectionId).catch(
			(error) => {
				toast.error(getError(error));
				return null;
			}
		);
		syncLoading = false;

		if (res) {
			const template = selectedProvider?.sync_success_label || 'Synced {{count}} files';
			toast.success($i18n.t(template, { count: res.synced ?? 0 }));
			await refreshConnections();
		}
	};

	const removeConnectionFiles = async () => {
		if (!selectedConnectionId) {
			return;
		}

		deletingFiles = true;
		const res = await deleteSourceConnectionFiles(localStorage.token, selectedConnectionId).catch(
			(error) => {
				toast.error(getError(error));
				return null;
			}
		);
		deletingFiles = false;

		if (res) {
			toast.success($i18n.t('Deleted {{count}} synced files', { count: res.deleted ?? 0 }));
			connectionFiles = [];
			await refreshConnections();
		}
	};

	const disconnectConnection = async () => {
		if (!selectedConnectionId) {
			return;
		}

		deletingConnection = true;
		const res = await deleteSourceConnection(localStorage.token, selectedConnectionId).catch(
			(error) => {
				toast.error(getError(error));
				return null;
			}
		);
		deletingConnection = false;

		if (res?.status) {
			toast.success($i18n.t('Connection removed successfully.'));
			await refreshConnections();
		}
	};

	onMount(async () => {
		const params = new URLSearchParams(window.location.search);
		if (params.get('connection_added')) {
			selectedProviderId = sessionStorage.getItem(LAST_PROVIDER_STORAGE_KEY) || '';
		}

		await refreshProviders();

		if (params.get('connection_added')) {
			toast.success($i18n.t('Connection added successfully.'));
			sessionStorage.removeItem(LAST_PROVIDER_STORAGE_KEY);
			params.delete('connection_added');
			const nextQuery = params.toString();
			const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}`;
			window.history.replaceState({}, '', nextUrl);
			await refreshProviders();
		}
	});
</script>

<div class="mb-3">
	<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('External Sources')}</div>

	<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

	<div class="text-xs text-gray-500 mb-3">
		{$i18n.t('Manage source connections once, choose resources, and sync them into Fireweed knowledge.')}
	</div>

	<div
		class="rounded-xl border border-gray-100 dark:border-gray-850 p-4 lg:p-0 lg:grid overflow-hidden {selectedProvider
			? 'lg:grid-cols-[320px_minmax(0,1fr)]'
			: 'lg:grid-cols-[360px_minmax(0,1fr)]'}"
	>
		{#if !selectedProvider}
			<ExternalSourcesLanding
				{providers}
				{providersLoading}
				{selectedProviderId}
				onSelectProvider={selectProvider}
			/>
		{:else}
			<ExternalSourcesSidebar
				{selectedProvider}
				{connectionsLoading}
				{connections}
				{selectedConnectionId}
				selectionLabel={selectionLabel()}
				connectLabel={getConnectLabel()}
				onBack={returnToProviders}
				onConnect={connectProvider}
				onSelectConnection={selectConnection}
			/>
		{/if}

		{#if selectedProvider}
			<ExternalSourcesConnectionDetail
				{selectedProvider}
				{selectedConnection}
				{knowledgeBases}
				bind:knowledgeBaseId
				bind:accessControl
				bind:selectedResources
				{selectionPreview}
				{connectionFiles}
				selectionLabel={selectionLabel()}
				emptySelectionMessage={emptySelectionMessage()}
				syncedFilesLabel={syncedFilesLabel()}
				noFilesMessage={noFilesMessage()}
				selectionActionLabel={getSelectionActionLabel()}
				previewHeading={previewHeading()}
				providersSelectedMessage={$i18n.t(
					'Connect {{provider}} to choose resources and sync them into your knowledge base.',
					{
						provider: selectedProvider.name
					}
				)}
				connectionEmptyMessage={$i18n.t(
					'Select a provider to start adding external source connections.'
				)}
				{filesLoading}
				{previewLoading}
				{syncLoading}
				{selectionLoading}
				{savingConnection}
				{deletingConnection}
				{deletingFiles}
				onSave={saveConnection}
				onSync={syncSelectedConnection}
				onPickResources={pickResources}
				onRemoveResource={removeResource}
				onRefreshSelectionPreview={refreshSelectionPreview}
				onRefreshConnectionFiles={refreshConnectionFiles}
				onRemoveConnectionFiles={removeConnectionFiles}
				onDisconnect={disconnectConnection}
			/>
		{/if}
	</div>
</div>

