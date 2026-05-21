<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let selectedProvider = null;
	export let connectionsLoading = false;
	export let connections = [];
	export let selectedConnectionId = '';
	export let selectionLabel = '';
	export let connectLabel = '';
	export let onBack = () => {};
	export let onConnect = () => {};
	export let onSelectConnection = (_connectionId: string) => {};
</script>

<div class="border-b lg:border-b-0 lg:border-r border-gray-100 dark:border-gray-850 p-3">
	<div class="mb-3">
		<div class="min-w-0">
			<div class="text-xs font-medium text-gray-500">{$i18n.t('Connections')}</div>
			<div class="flex items-center gap-2 mt-1 min-w-0">
				<button
					class="inline-flex h-7 w-7 items-center justify-center rounded-full border border-gray-200 bg-gray-50 text-gray-600 transition hover:bg-gray-100 dark:border-gray-800 dark:bg-gray-900/50 dark:text-gray-300 dark:hover:bg-gray-900"
					type="button"
					aria-label={$i18n.t('Back to providers')}
					on:click={onBack}
				>
					<span aria-hidden="true">&lt;</span>
				</button>
				<div class="text-sm font-medium truncate">{selectedProvider?.name}</div>
			</div>
		</div>
	</div>

	<div class="mb-3">
		<button
			class="flex w-full items-center justify-center rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-xs font-medium text-gray-700 transition hover:border-gray-300 hover:bg-white dark:border-gray-800 dark:bg-gray-900/40 dark:text-gray-200 dark:hover:border-gray-700 dark:hover:bg-gray-900 disabled:opacity-60"
			type="button"
			disabled={!selectedProvider}
			on:click={onConnect}
		>
			{connectLabel}
		</button>
	</div>

	{#if connectionsLoading}
		<div class="py-6 flex justify-center">
			<Spinner className="size-4" />
		</div>
	{:else if connections.length === 0}
		<div class="rounded-xl bg-gray-50 dark:bg-gray-900/40 p-3 text-xs text-gray-500">
			{$i18n.t('No connections for this provider yet.')}
		</div>
	{:else}
		<div class="space-y-2">
			{#each connections as connection}
				<button
					class="w-full rounded-xl border px-3 py-3 text-left transition {selectedConnectionId === connection.id
						? 'border-gray-700 bg-gray-900 text-gray-100'
						: 'border-gray-200 bg-gray-50 text-gray-800 hover:bg-gray-100 dark:border-gray-800 dark:bg-gray-900/50 dark:text-gray-200 dark:hover:bg-gray-900'}"
					type="button"
					on:click={() => {
						onSelectConnection(connection.id);
					}}
				>
					<div class="text-sm font-medium truncate">{connection.display_name}</div>
					<div class="text-xs mt-1 opacity-70 truncate">
						{connection.account_email || selectedProvider?.name || $i18n.t('Connection')}
					</div>
					<div class="text-xs mt-2 opacity-60">
						{selectionLabel}: {(connection.selected_resources || []).length}
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>
