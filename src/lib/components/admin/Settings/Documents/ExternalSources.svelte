<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		deleteGDriveFiles,
		deleteSharePointFiles,
		getGDriveFiles,
		getSharePointFiles,
		getSharePointSites,
		syncGDrive,
		syncSharePoint,
		updateSourcesConfig
	} from '$lib/apis/integrations';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';

	const i18n = getContext('i18n');

	export let sourceConfig = {
		gdrive: {
			enabled: false,
			service_account_json: '',
			watch_folder_id: '',
			webhook_token: '',
			knowledge_base_id: '',
			access_control: {}
		},
		sharepoint: {
			enabled: false,
			tenant_id: '',
			client_id: '',
			client_secret: '',
			site_url: '',
			knowledge_base_id: '',
			access_control: {}
		}
	};

	export let knowledgeBases = [];

	let gdriveFiles = [];
	let sharepointFiles = [];
	let sharepointSites = [];
	let selectedProvider = 'gdrive';

	const providers = [
		{
			id: 'gdrive',
			name: 'Google Drive',
			description: 'Shared folder sync'
		},
		{
			id: 'sharepoint',
			name: 'SharePoint',
			description: 'Document library sync'
		}
	];

	let gdriveBusy = false;
	let sharepointBusy = false;
	let gdriveFilesLoading = false;
	let sharepointFilesLoading = false;
	let sharepointSitesLoading = false;

	const showError = (error: any) => {
		toast.error(`${error}`);
	};

	const persistSourceConfig = async () => {
		const res = await updateSourcesConfig(localStorage.token, sourceConfig).catch((error) => {
			showError(error);
			return null;
		});

		return res;
	};

	const refreshGDriveFiles = async () => {
		gdriveFilesLoading = true;
		const res = await getGDriveFiles(localStorage.token).catch((error) => {
			showError(error);
			return null;
		});
		gdriveFilesLoading = false;

		if (res) {
			gdriveFiles = res.files ?? [];
		}
	};

	const refreshSharePointFiles = async () => {
		sharepointFilesLoading = true;
		const res = await getSharePointFiles(localStorage.token).catch((error) => {
			showError(error);
			return null;
		});
		sharepointFilesLoading = false;

		if (res) {
			sharepointFiles = res.files ?? [];
		}
	};

	const syncGoogleDrive = async () => {
		const persisted = await persistSourceConfig();
		if (!persisted) {
			return;
		}

		gdriveBusy = true;
		const res = await syncGDrive(localStorage.token, {
			folder_id: sourceConfig.gdrive.watch_folder_id || null,
			knowledge_base_id: sourceConfig.gdrive.knowledge_base_id || null,
			access_control: sourceConfig.gdrive.access_control
		}).catch((error) => {
			showError(error);
			return null;
		});
		gdriveBusy = false;

		if (res) {
			toast.success(
				$i18n.t('Synced {{count}} Google Drive files', {
					count: res.synced ?? 0
				})
			);
			await refreshGDriveFiles();
		}
	};

	const syncSharePointSource = async () => {
		const persisted = await persistSourceConfig();
		if (!persisted) {
			return;
		}

		sharepointBusy = true;
		const res = await syncSharePoint(localStorage.token, {
			site_url: sourceConfig.sharepoint.site_url || null,
			knowledge_base_id: sourceConfig.sharepoint.knowledge_base_id || null,
			access_control: sourceConfig.sharepoint.access_control
		}).catch((error) => {
			showError(error);
			return null;
		});
		sharepointBusy = false;

		if (res) {
			toast.success(
				$i18n.t('Synced {{count}} SharePoint files', {
					count: res.synced ?? 0
				})
			);
			await refreshSharePointFiles();
		}
	};

	const clearGDriveFiles = async () => {
		gdriveBusy = true;
		const res = await deleteGDriveFiles(localStorage.token).catch((error) => {
			showError(error);
			return null;
		});
		gdriveBusy = false;

		if (res) {
			toast.success(
				$i18n.t('Deleted {{count}} Google Drive files', {
					count: res.deleted ?? 0
				})
			);
			gdriveFiles = [];
		}
	};

	const clearSharePointFiles = async () => {
		sharepointBusy = true;
		const res = await deleteSharePointFiles(localStorage.token).catch((error) => {
			showError(error);
			return null;
		});
		sharepointBusy = false;

		if (res) {
			toast.success(
				$i18n.t('Deleted {{count}} SharePoint files', {
					count: res.deleted ?? 0
				})
			);
			sharepointFiles = [];
		}
	};

	const loadSharePointSites = async () => {
		const persisted = await persistSourceConfig();
		if (!persisted) {
			return;
		}

		sharepointSitesLoading = true;
		const res = await getSharePointSites(localStorage.token).catch((error) => {
			showError(error);
			return null;
		});
		sharepointSitesLoading = false;

		if (res) {
			sharepointSites = res.sites ?? [];
		}
	};

	const formatFileMeta = (file) => {
		const data = file?.meta?.data ?? {};
		return data.modified_time || file.updated_at || file.created_at || '';
	};

	onMount(async () => {
		await Promise.all([refreshGDriveFiles(), refreshSharePointFiles()]);
	});
</script>

<div class="mb-3">
	<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('External Sources')}</div>

	<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

	<div class="text-xs text-gray-500 mb-3">
		{$i18n.t('Use Save below to persist configuration changes. Sync actions run immediately.')}
	</div>

	<div
		class="rounded-xl border border-gray-100 dark:border-gray-850 p-4 lg:p-0 lg:grid lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-0 overflow-hidden"
	>
		<div class="border-b lg:border-b-0 lg:border-r border-gray-100 dark:border-gray-850 p-2 lg:p-3">
			<div class="text-xs font-medium text-gray-500 px-2 py-1">
				{$i18n.t('Connections')}
			</div>
			<div class="space-y-1">
				{#each providers as provider}
					<button
						class="w-full rounded-xl px-3 py-3 text-left transition {selectedProvider === provider.id
							? 'bg-black text-white dark:bg-white dark:text-black'
							: 'bg-transparent hover:bg-gray-50 dark:hover:bg-gray-900/50'}"
						type="button"
						on:click={() => {
							selectedProvider = provider.id;
						}}
					>
						<div class="flex items-start justify-between gap-2">
							<div class="min-w-0">
								<div class="text-sm font-medium truncate">{$i18n.t(provider.name)}</div>
								<div class="text-xs opacity-70 truncate">
									{$i18n.t(provider.description)}
								</div>
							</div>
							<div class="shrink-0 text-[11px] opacity-70">
								{provider.id === 'gdrive' ? gdriveFiles.length : sharepointFiles.length}
							</div>
						</div>
					</button>
				{/each}
			</div>
		</div>

		<div class="p-4 space-y-4">
			{#if selectedProvider === 'gdrive'}
				<div class="space-y-3">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium">{$i18n.t('Google Drive')}</div>
						<div class="text-xs text-gray-500">
							{$i18n.t('Sync a shared Drive folder into a knowledge base.')}
						</div>
					</div>
					<Switch bind:state={sourceConfig.gdrive.enabled} />
				</div>

				<div class="space-y-2">
					<div class="text-xs font-medium">{$i18n.t('Service Account JSON')}</div>
					<Textarea
						bind:value={sourceConfig.gdrive.service_account_json}
						rows={5}
						placeholder={$i18n.t('Paste the Google service account JSON or a path to it')}
					/>
				</div>

				<div class="grid gap-3 lg:grid-cols-2">
					<div class="space-y-1">
						<div class="text-xs font-medium">{$i18n.t('Folder ID')}</div>
						<input
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={sourceConfig.gdrive.watch_folder_id}
							placeholder={$i18n.t('Shared Google Drive folder ID')}
						/>
					</div>

					<div class="space-y-1">
						<div class="text-xs font-medium">{$i18n.t('Webhook Token')}</div>
						<div class="w-full rounded-lg px-3 py-2 bg-gray-50 dark:bg-gray-850">
							<SensitiveInput
								required={false}
								bind:value={sourceConfig.gdrive.webhook_token}
								placeholder={$i18n.t('Optional webhook token')}
							/>
						</div>
					</div>
				</div>

				<div class="space-y-1">
					<div class="text-xs font-medium">{$i18n.t('Target Knowledge Base')}</div>
					<select
						class="dark:bg-gray-900 w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
						bind:value={sourceConfig.gdrive.knowledge_base_id}
					>
						<option value="">{$i18n.t('Create or use default sync knowledge base')}</option>
						{#each knowledgeBases as knowledgeBase}
							<option value={knowledgeBase.id}>{knowledgeBase.name}</option>
						{/each}
					</select>
				</div>

				<div>
					<AccessControl bind:accessControl={sourceConfig.gdrive.access_control} />
				</div>

				<div class="flex flex-wrap gap-2">
					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-black text-white dark:bg-white dark:text-black disabled:opacity-60"
						type="button"
						disabled={gdriveBusy}
						on:click={syncGoogleDrive}
					>
						{#if gdriveBusy}
							<span class="inline-flex items-center gap-1">
								<Spinner className="size-3" />
								{$i18n.t('Syncing')}
							</span>
						{:else}
							{$i18n.t('Sync Now')}
						{/if}
					</button>

					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-850"
						type="button"
						disabled={gdriveFilesLoading}
						on:click={refreshGDriveFiles}
					>
						{$i18n.t('Refresh Files')}
					</button>

					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-850 text-red-600 dark:text-red-400"
						type="button"
						disabled={gdriveBusy}
						on:click={clearGDriveFiles}
					>
						{$i18n.t('Delete Synced Files')}
					</button>
				</div>

				<div class="rounded-lg bg-gray-50 dark:bg-gray-900/40 px-3 py-2">
					<div class="text-xs font-medium mb-1">
						{$i18n.t('Synced Files')} ({gdriveFiles.length})
					</div>
					{#if gdriveFiles.length > 0}
						<div class="space-y-1">
							{#each gdriveFiles.slice(0, 5) as file}
								<div class="flex items-center justify-between gap-2 text-xs">
									<div class="truncate">{file.filename}</div>
									<div class="text-gray-500 shrink-0">{formatFileMeta(file)}</div>
								</div>
							{/each}
						</div>
					{:else}
						<div class="text-xs text-gray-500">
							{$i18n.t('No Google Drive files have been synced yet.')}
						</div>
					{/if}
				</div>
				</div>
			{:else if selectedProvider === 'sharepoint'}
				<div class="space-y-3">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium">{$i18n.t('SharePoint')}</div>
						<div class="text-xs text-gray-500">
							{$i18n.t('Sync a SharePoint document library into a knowledge base.')}
						</div>
					</div>
					<Switch bind:state={sourceConfig.sharepoint.enabled} />
				</div>

				<div class="grid gap-3 lg:grid-cols-2">
					<div class="space-y-1">
						<div class="text-xs font-medium">{$i18n.t('Tenant ID')}</div>
						<input
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={sourceConfig.sharepoint.tenant_id}
							placeholder={$i18n.t('Azure AD tenant ID')}
						/>
					</div>

					<div class="space-y-1">
						<div class="text-xs font-medium">{$i18n.t('Client ID')}</div>
						<input
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={sourceConfig.sharepoint.client_id}
							placeholder={$i18n.t('App registration client ID')}
						/>
					</div>
				</div>

				<div class="space-y-1">
					<div class="text-xs font-medium">{$i18n.t('Client Secret')}</div>
					<div class="w-full rounded-lg px-3 py-2 bg-gray-50 dark:bg-gray-850">
						<SensitiveInput
							required={false}
							bind:value={sourceConfig.sharepoint.client_secret}
							placeholder={$i18n.t('App registration client secret')}
						/>
					</div>
				</div>

				<div class="grid gap-3 lg:grid-cols-2">
					<div class="space-y-1">
						<div class="text-xs font-medium">{$i18n.t('Site URL')}</div>
						<input
							class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={sourceConfig.sharepoint.site_url}
							placeholder={$i18n.t('https://tenant.sharepoint.com/sites/example')}
						/>
					</div>

					<div class="space-y-1">
						<div class="text-xs font-medium">{$i18n.t('Target Knowledge Base')}</div>
						<select
							class="dark:bg-gray-900 w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={sourceConfig.sharepoint.knowledge_base_id}
						>
							<option value="">{$i18n.t('Create or use default sync knowledge base')}</option>
							{#each knowledgeBases as knowledgeBase}
								<option value={knowledgeBase.id}>{knowledgeBase.name}</option>
							{/each}
						</select>
					</div>
				</div>

				<div>
					<AccessControl bind:accessControl={sourceConfig.sharepoint.access_control} />
				</div>

				<div class="flex flex-wrap gap-2">
					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-black text-white dark:bg-white dark:text-black disabled:opacity-60"
						type="button"
						disabled={sharepointBusy}
						on:click={syncSharePointSource}
					>
						{#if sharepointBusy}
							<span class="inline-flex items-center gap-1">
								<Spinner className="size-3" />
								{$i18n.t('Syncing')}
							</span>
						{:else}
							{$i18n.t('Sync Now')}
						{/if}
					</button>

					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-850"
						type="button"
						disabled={sharepointFilesLoading}
						on:click={refreshSharePointFiles}
					>
						{$i18n.t('Refresh Files')}
					</button>

					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-850"
						type="button"
						disabled={sharepointSitesLoading}
						on:click={loadSharePointSites}
					>
						{$i18n.t('List Sites')}
					</button>

					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-850 text-red-600 dark:text-red-400"
						type="button"
						disabled={sharepointBusy}
						on:click={clearSharePointFiles}
					>
						{$i18n.t('Delete Synced Files')}
					</button>
				</div>

				<div class="rounded-lg bg-gray-50 dark:bg-gray-900/40 px-3 py-2">
					<div class="text-xs font-medium mb-1">
						{$i18n.t('Synced Files')} ({sharepointFiles.length})
					</div>
					{#if sharepointFiles.length > 0}
						<div class="space-y-1">
							{#each sharepointFiles.slice(0, 5) as file}
								<div class="flex items-center justify-between gap-2 text-xs">
									<div class="truncate">{file.filename}</div>
									<div class="text-gray-500 shrink-0">{formatFileMeta(file)}</div>
								</div>
							{/each}
						</div>
					{:else}
						<div class="text-xs text-gray-500">
							{$i18n.t('No SharePoint files have been synced yet.')}
						</div>
					{/if}
				</div>

				{#if sharepointSites.length > 0}
					<div class="rounded-lg bg-gray-50 dark:bg-gray-900/40 px-3 py-2">
						<div class="text-xs font-medium mb-1">{$i18n.t('Available Sites')}</div>
						<div class="space-y-1">
							{#each sharepointSites as site}
								<div class="text-xs">
									<div class="font-medium">{site.name || site.id}</div>
									<div class="text-gray-500 break-all">{site.url || site.id}</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
