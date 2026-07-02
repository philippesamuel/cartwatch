<script setup>
useHead({
  meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
  link: [{ rel: 'icon', href: '/favicon.ico' }],
  htmlAttrs: { lang: 'en' }
})

useSeoMeta({
  title: 'cartwatch',
  description: 'Track your grocery prices over time.'
})
</script>

<template>
  <UApp>
    <UHeader>
      <template #left>
        <NuxtLink to="/" class="flex items-center gap-2 font-semibold text-lg">
          <AppLogo class="w-auto h-6 shrink-0" />
        </NuxtLink>

        <UNavigationMenu
          :items="[
            { label: 'Price History', to: '/prices', icon: 'i-lucide-trending-up' },
            { label: 'Products', to: '/products', icon: 'i-lucide-table' },
            { label: 'Data Quality', to: '/data-quality', icon: 'i-lucide-shield-alert' }
          ]"
          class="ml-4"
        />
      </template>

      <template #right>
        <UColorModeButton />
      </template>
    </UHeader>

    <UMain>
      <NuxtPage />
    </UMain>

    <UFooter>
      <template #left>
        <p class="text-sm text-muted">
          cartwatch © {{ new Date().getFullYear() }}
        </p>
      </template>
    </UFooter>
  </UApp>
</template>
