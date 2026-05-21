<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';

	const i18n = getContext('i18n');

	export let selectedProvider = null;
	export let selectedConnection = null;
	export let knowledgeBases = [];
	export let knowledgeBaseId = '';
	export let accessControl = {};
	export let selectedResources = [];
	export let selectionPreview = null;
	export let connectionFiles = [];
	export let selectionLabel = '';
	export let emptySelectionMessage = '';
	export let syncedFilesLabel = '';
	export let noFilesMessage = '';
	export let selectionActionLabel = '';
	export let previewHeading = '';
	export let providersSelectedMessage = '';
	export let connectionEmptyMessage = '';
	export let filesLoading = false;
	export let previewLoading = false;
	export let syncLoading = false;
	export let selectionLoading = false;
	export let savingConnection = false;
	export let deletingConnection = false;
	export let deletingFiles = false;
	export let onSave = () => {};
	export let onSync = () => {};
	export let onPickResources = () => {};
	export let onRemoveResource = (_resourceId: string) => {};
	export let onRefreshSelectionPreview = () => {};
	export let onRefreshConnectionFiles = () => {};
	export let onRemoveConnectionFiles = () => {};
	export let onDisconnect = () => {};
</script>

<div class="p-4">
	{#if selectedConnection}
		<div class="space-y-4">
			<div class="flex items-center justify-between gap-3">
				<div>
					<div class="text-sm font-medium">{selectedConnection.display_name}</div>
					<div class="text-xs text-gray-500">
						{selectedConnection.account_email}
					</div>
				</div>

				<div class="flex gap-2">
					<button
						class="px-3 py-1.5 rounded-full text-xs font-medium bg-black text-white transition hover:bg-gray-800 active:bg-gray-700 dark:bg-white dark:text-black dark:hover:bg-gray-200 dark:active:bg-gray-300"
						type="button"
						disabled={syncLoading}
						on:click={onSync}
					>
						{#if syncLoading}
							<span class="inline-flex items-center gap-1">
								<Spinner className="size-3" />
								{$i18n.t('Syncing')}
							</span>
						{:else}
							{$i18n.t('Re-sync')}
						{/if}
					</button>
				</div>
			</div>

			<div class="space-y-1">
				<div class="text-xs font-medium">{$i18n.t('Target Knowledge Base')}</div>
				<select
					class="dark:bg-gray-900 w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
					bind:value={knowledgeBaseId}
					on:change={onSave}
				>
					<option value="">{$i18n.t('Create or use default sync knowledge base')}</option>
					{#each knowledgeBases as knowledgeBase}
						<option value={knowledgeBase.id}>{knowledgeBase.name}</option>
					{/each}
				</select>
			</div>

			<div>
				<AccessControl bind:accessControl onChange={onSave} />
			</div>

			<div class="px-2 py-1">
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-3">
						<div class="text-xs font-medium text-gray-500">{selectionLabel}</div>
						<button
							class="selection-add-button inline-flex h-7 w-7 items-center justify-center rounded-full border border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-800 dark:bg-gray-900/50 dark:text-gray-200"
							type="button"
							title={selectionActionLabel}
							aria-label={selectionActionLabel}
							disabled={selectionLoading}
							on:click={onPickResources}
						>
							{#if selectionLoading}
								<Spinner className="size-3" />
							{:else}
								<Plus className="size-3" />
							{/if}
						</button>
					</div>
					<div class="text-xs text-gray-500">{selectedResources.length}</div>
				</div>

				{#if selectedResources.length > 0}
					<div class="space-y-2 pl-4">
						{#each selectedResources as resource}
							<div class="flex items-center gap-2 text-xs">
								<button
									class="inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-gray-700 text-[11px] transition hover:bg-red-50 hover:text-red-600 active:bg-red-100 dark:bg-gray-850 dark:text-gray-300 dark:hover:bg-red-950/40 dark:hover:text-red-400 dark:active:bg-red-950/60"
									type="button"
									aria-label={$i18n.t('Remove')}
									title={$i18n.t('Remove')}
									on:click={() => {
										onRemoveResource(resource.id);
									}}
								>
									<span aria-hidden="true">-</span>
								</button>
								<div class="truncate">{resource.name}</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-xs text-gray-500">
						{emptySelectionMessage}
					</div>
				{/if}
			</div>

			<div class="px-2 py-1">
				<div class="flex items-center justify-between mb-2">
					<div class="text-xs font-medium text-gray-500">
						{previewHeading}
					</div>
					<button
						class="text-xs text-gray-500"
						type="button"
						disabled={previewLoading}
						on:click={onRefreshSelectionPreview}
					>
						{$i18n.t('Refresh')}
					</button>
				</div>

				{#if previewLoading}
					<div class="py-4 flex justify-center">
						<Spinner className="size-4" />
					</div>
				{:else if selectionPreview?.folders?.length > 0}
					<div class="space-y-3">
						{#each selectionPreview.folders as folder}
							<div class="rounded-md border border-gray-200 dark:border-gray-800 px-3 py-2">
								<div class="flex items-center justify-between gap-2 text-xs mb-2">
									<div class="font-medium truncate">{folder.name}</div>
									<div class="text-gray-500 shrink-0">
										{folder.file_count} {$i18n.t('files')}
									</div>
								</div>

								{#if folder.files?.length > 0}
									<div class="space-y-1">
										{#each folder.files as file}
											<div class="flex items-center justify-between gap-2 text-xs">
												<div class="truncate">{file.name}</div>
												<div class="text-gray-500 shrink-0">
													{file.mime_type?.split('/').pop() || ''}
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-xs text-gray-500">
										{$i18n.t('No files found in this folder.')}
									</div>
								{/if}

								{#if folder.traversed_folders > 0}
									<div class="text-xs text-gray-500 mt-2">
										{$i18n.t('Includes {{count}} nested folders.', {
											count: folder.traversed_folders
										})}
									</div>
								{/if}
							</div>
						{/each}

						{#if selectionPreview?.truncated}
							<div class="text-xs text-gray-500">
								{$i18n.t('Preview truncated. Showing the first {{count}} files.', {
									count: 100
								})}
							</div>
						{/if}
					</div>
				{:else}
					<div class="text-xs text-gray-500">
						{$i18n.t('Select folders to preview the files they contain.')}
					</div>
				{/if}
			</div>

			<div class="px-2 py-1">
				<div class="flex items-center justify-between mb-2">
					<div class="text-xs font-medium text-gray-500">{syncedFilesLabel}</div>
					<div class="flex gap-2">
						<button
							class="text-xs text-gray-500"
							type="button"
							disabled={filesLoading}
							on:click={onRefreshConnectionFiles}
						>
							{$i18n.t('Refresh')}
						</button>
						<button
							class="text-xs text-red-600 dark:text-red-400"
							type="button"
							disabled={deletingFiles}
							on:click={onRemoveConnectionFiles}
						>
							{$i18n.t('Delete All')}
						</button>
					</div>
				</div>

				{#if filesLoading}
					<div class="py-4 flex justify-center">
						<Spinner className="size-4" />
					</div>
				{:else if connectionFiles.length > 0}
					<div class="space-y-1">
						{#each connectionFiles.slice(0, 10) as file}
							<div class="flex items-center justify-between gap-2 text-xs">
								<div class="truncate">{file.filename}</div>
								<div class="text-gray-500 shrink-0">
									{file?.meta?.data?.folder_name || ''}
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-xs text-gray-500">
						{noFilesMessage}
					</div>
				{/if}
			</div>

			<div class="flex justify-end gap-2 pt-1">
				<button
					class="px-3 py-1.5 rounded-full text-xs font-medium text-red-600 transition hover:bg-red-50 active:bg-red-100 dark:text-red-400 dark:bg-gray-850 dark:hover:bg-red-950/40 dark:active:bg-red-950/60"
					type="button"
					disabled={deletingConnection}
					on:click={onDisconnect}
				>
					{#if deletingConnection}
						<span class="inline-flex items-center gap-1">
							<Spinner className="size-3" />
							{$i18n.t('Removing')}
						</span>
					{:else}
						{$i18n.t('Disconnect')}
					{/if}
				</button>

				<button
					class="px-3 py-1.5 rounded-full text-xs font-medium bg-black text-white dark:bg-white dark:text-black"
					type="button"
					disabled={savingConnection}
					on:click={onSave}
				>
					{#if savingConnection}
						<span class="inline-flex items-center gap-1">
							<Spinner className="size-3" />
							{$i18n.t('Saving')}
						</span>
					{:else}
						{$i18n.t('Save')}
					{/if}
				</button>
			</div>
		</div>
	{:else if selectedProvider}
		<div class="rounded-xl bg-gray-50 dark:bg-gray-900/40 p-4 text-sm text-gray-500">
			{providersSelectedMessage}
		</div>
	{:else}
		<div class="rounded-xl bg-gray-50 dark:bg-gray-900/40 p-4 text-sm text-gray-500">
			{connectionEmptyMessage}
		</div>
	{/if}
</div>

<style>
	.selection-add-button {
		transition:
			background 140ms ease,
			border-color 140ms ease,
			color 140ms ease,
			box-shadow 140ms ease,
			transform 120ms ease;
	}

	.selection-add-button:not(:disabled):hover,
	.selection-add-button:not(:disabled):focus-visible {
		background: linear-gradient(
			180deg,
			rgb(var(--brand-purple-rgb) / 0.9) 0%,
			rgb(var(--brand-purple-rgb) / 0.78) 100%
		);
		border-color: rgb(var(--brand-purple-rgb) / 0.62);
		color: #fff;
		box-shadow:
			inset 0 0 0 1px rgb(255 255 255 / 0.12),
			0 8px 18px rgb(var(--brand-purple-rgb) / 0.2);
		transform: translateY(-1px);
	}

	.selection-add-button:not(:disabled):active {
		background: linear-gradient(
			180deg,
			rgb(var(--brand-purple-rgb) / 0.96) 0%,
			rgb(var(--brand-purple-rgb) / 0.84) 100%
		);
		color: #fff;
		transform: translateY(0);
	}
</style>
