<script setup lang="ts">
useSeoMeta({ title: 'Price History · cartwatch' })

const supabase = useSupabaseClient()

type ProductHit = { id: string; name: string; short_name: string; unit: string | null }

const query = ref('')
const searchResults = ref<ProductHit[]>([])
const searching = ref(false)

// Persisted list of charts (one per product), kept in this browser.
const STORAGE_KEY = 'cartwatch:price-charts'
const products = ref<ProductHit[]>([])

onMounted(() => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) products.value = JSON.parse(saved)
  } catch {
    // ignore malformed storage
  }
})

watch(products, (val) => {
  if (import.meta.client) localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
}, { deep: true })

const addedIds = computed(() => new Set(products.value.map(p => p.id)))

async function searchProducts() {
  if (query.value.length < 2) {
    searchResults.value = []
    return
  }
  searching.value = true
  const { data } = await supabase
    .from('canonical_products')
    .select('id, name, short_name, units ( symbol )')
    .ilike('name', `%${query.value}%`)
    .limit(10)
  searchResults.value = (data ?? []).map((r: any) => ({
    id: r.id,
    name: r.name,
    short_name: r.short_name,
    unit: r.units?.symbol ?? null
  }))
  searching.value = false
}

function addProduct(product: ProductHit) {
  if (!addedIds.value.has(product.id)) products.value.push(product)
  query.value = ''
  searchResults.value = []
}

function removeProduct(id: string) {
  products.value = products.value.filter(p => p.id !== id)
}
</script>

<template>
  <UContainer class="py-8 max-w-4xl">
    <div class="mb-6">
      <h1 class="text-2xl font-bold mb-1">
        Price History
      </h1>
      <p class="text-muted text-sm">
        Add a chart per product to compare price trends across stores. Your charts are saved in this browser.
      </p>
    </div>

    <div class="relative mb-8">
      <UInput
        v-model="query"
        placeholder="Search products to add a chart… e.g. milk, eggs"
        icon="i-lucide-search"
        size="lg"
        class="w-full"
        :loading="searching"
        @input="searchProducts"
      />
      <div
        v-if="searchResults.length"
        class="absolute z-10 w-full mt-1 bg-background border border-default rounded-lg shadow-lg overflow-hidden"
      >
        <button
          v-for="product in searchResults"
          :key="product.id"
          class="w-full text-left px-4 py-2.5 hover:bg-elevated flex items-center gap-3 transition-colors disabled:opacity-50"
          :disabled="addedIds.has(product.id)"
          @click="addProduct(product)"
        >
          <UIcon name="i-lucide-package" class="text-muted shrink-0" />
          <span>{{ product.name }}</span>
          <span
            v-if="addedIds.has(product.id)"
            class="ml-auto text-xs text-primary flex items-center gap-1"
          >
            <UIcon name="i-lucide-check" /> added
          </span>
          <span v-else class="text-muted text-sm ml-auto">{{ product.short_name }}</span>
        </button>
      </div>
    </div>

    <div v-if="products.length" class="space-y-6">
      <ProductChart
        v-for="product in products"
        :key="product.id"
        :product="product"
        @remove="removeProduct(product.id)"
      />
    </div>

    <div v-else class="text-center py-16 text-muted">
      <UIcon name="i-lucide-line-chart" class="text-4xl mb-2" />
      <p>Search for a product above to add your first chart.</p>
    </div>
  </UContainer>
</template>
