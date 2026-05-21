<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let providers = [];
	export let providersLoading = false;
	export let selectedProviderId = '';
	export let onSelectProvider = (_providerId: string) => {};

	const getProviderBadge = (provider: any) => {
		const parts = `${provider?.name || ''}`.trim().split(/\s+/).filter(Boolean);
		return parts.slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'EX';
	};
</script>

<div class="border-b lg:border-b-0 lg:border-r border-gray-100 dark:border-gray-850 p-4">
	<div class="flex items-center justify-between mb-3">
		<div class="text-xs font-medium text-gray-500">{$i18n.t('Providers')}</div>
		<div class="text-[11px] uppercase tracking-[0.18em] text-gray-500">
			{providers.length} {$i18n.t('available')}
		</div>
	</div>

	{#if providersLoading}
		<div class="py-6 flex justify-center">
			<Spinner className="size-4" />
		</div>
	{:else if providers.length === 0}
		<div class="rounded-xl bg-gray-50 dark:bg-gray-900/40 p-3 text-xs text-gray-500">
			{$i18n.t('No providers available yet.')}
		</div>
	{:else}
		<div class="space-y-3">
			{#each providers as provider}
				<button
					class="group w-full rounded-2xl border px-4 py-4 text-left transition {selectedProviderId === provider.id
						? 'border-gray-700 bg-gray-900 text-gray-100 shadow-[0_0_0_1px_rgba(255,255,255,0.04)]'
						: 'border-gray-200 bg-gray-50 text-gray-800 hover:border-gray-300 hover:bg-white dark:border-gray-800 dark:bg-gray-900/50 dark:text-gray-200 dark:hover:border-gray-700 dark:hover:bg-gray-900'}"
					type="button"
					on:click={() => {
						onSelectProvider(provider.id);
					}}
				>
					<div class="flex items-start gap-3">
						<div class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-gray-200 bg-white text-xs font-semibold text-gray-700 transition group-hover:border-gray-300 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200 dark:group-hover:border-gray-600">
							{getProviderBadge(provider)}
						</div>
						<div class="min-w-0">
							<div class="flex items-center justify-between gap-3">
								<div class="text-sm font-medium truncate">{provider.name}</div>
								<div class="text-[11px] uppercase tracking-[0.16em] opacity-50">
									{$i18n.t('Source')}
								</div>
							</div>
							<div class="text-xs mt-1 opacity-70 line-clamp-3">
								{provider.description}
							</div>
						</div>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>

<div class="p-4 lg:p-6">
	<div class="h-full rounded-2xl border border-gray-100 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.06),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0))] px-5 py-5 dark:border-gray-850">
		<div class="max-w-2xl">
			<div class="text-[11px] uppercase tracking-[0.22em] text-gray-500">
				{$i18n.t('Connection Flow')}
			</div>
			<div class="mt-3 text-xl font-semibold leading-tight">
				{$i18n.t('Connect once, sync repeatedly, manage each source in one place.')}
			</div>
			<div class="mt-3 max-w-xl text-sm text-gray-400">
				{$i18n.t('Pick a provider to start a focused setup flow. Each provider can hold multiple connections over time, so this view stays usable as more sources are added.')}
			</div>
		</div>

		<div class="mt-6 grid gap-3 md:grid-cols-3">
			<div class="rounded-2xl border border-gray-100/80 px-4 py-4 dark:border-gray-800">
				<div class="text-[11px] uppercase tracking-[0.18em] text-gray-500">01</div>
				<div class="mt-2 text-sm font-medium">{$i18n.t('Choose Provider')}</div>
				<div class="mt-1 text-xs text-gray-500">
					{$i18n.t('Start with the source type you want to connect.')}
				</div>
			</div>
			<div class="rounded-2xl border border-gray-100/80 px-4 py-4 dark:border-gray-800">
				<div class="text-[11px] uppercase tracking-[0.18em] text-gray-500">02</div>
				<div class="mt-2 text-sm font-medium">{$i18n.t('Authorize Account')}</div>
				<div class="mt-1 text-xs text-gray-500">
					{$i18n.t('Create one or more reusable account connections for that provider.')}
				</div>
			</div>
			<div class="rounded-2xl border border-gray-100/80 px-4 py-4 dark:border-gray-800">
				<div class="text-[11px] uppercase tracking-[0.18em] text-gray-500">03</div>
				<div class="mt-2 text-sm font-medium">{$i18n.t('Select And Sync')}</div>
				<div class="mt-1 text-xs text-gray-500">
					{$i18n.t('Choose resources, preview what will sync, then re-sync whenever content changes.')}
				</div>
			</div>
		</div>
	</div>
</div>
