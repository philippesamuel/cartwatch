<script setup lang="ts">
useSeoMeta({ title: 'Products · cartwatch' })
</script>

<template>
  <UContainer class="py-8 max-w-7xl">
    <div class="mb-6">
      <h1 class="text-2xl font-bold mb-1">
        Products
      </h1>
      <p class="text-muted text-sm">
        Every canonical product with how often it's been observed and its price statistics across stores.
      </p>
    </div>

    <ProductStatsTable />
  </UContainer>
</template>
