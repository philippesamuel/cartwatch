<script setup lang="ts">
useSeoMeta({ title: 'Price History · cartwatch' })

const supabase = useSupabaseClient()

type ProductHit = { id: string; name: string; short_name: string; unit: string | null; obs?: number }

const query = ref('')
const focused = ref(false)

// Persisted state, kept in this browser.
const STORAGE_KEY = 'cartwatch:price-charts'
const PERROW_KEY = 'cartwatch:charts-per-row'
const JITTER_KEY = 'cartwatch:jitter'
const MINOBS_KEY = 'cartwatch:min-obs'
const products = ref<ProductHit[]>([])
const perRow = ref(1)
const jitter = ref(true)
const minObs = ref(5)

// Every product with its observation count, most-observed first — powers an
// instant, browsable dropdown so you can pick without typing an exact name.
const allProducts = ref<ProductHit[]>([])

onMounted(async () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) products.value = JSON.parse(saved)
    const savedPerRow = Number(localStorage.getItem(PERROW_KEY))
    if (savedPerRow >= 1 && savedPerRow <= 3) perRow.value = savedPerRow
    const savedJitter = localStorage.getItem(JITTER_KEY)
    if (savedJitter !== null) jitter.value = savedJitter === 'true'
    const savedMinObs = Number(localStorage.getItem(MINOBS_KEY))
    if (Number.isFinite(savedMinObs) && savedMinObs >= 0) minObs.value = savedMinObs
  } catch {
    // ignore malformed storage
  }

  const [{ data: stats }, { data: prods }] = await Promise.all([
    supabase.from('mv_product_stats').select('canonical_product_name, line_item_count'),
    supabase.from('canonical_products').select('id, name, short_name, units ( symbol )')
  ])
  const obs = new Map<string, number>()
  for (const r of stats ?? []) {
    obs.set(r.canonical_product_name, (obs.get(r.canonical_product_name) ?? 0) + Number(r.line_item_count))
  }
  allProducts.value = (prods ?? [])
    .map((r: any) => ({
      id: r.id,
      name: r.name,
      short_name: r.short_name,
      unit: r.units?.symbol ?? null,
      obs: obs.get(r.name) ?? 0
    }))
    .sort((a, b) => (b.obs ?? 0) - (a.obs ?? 0))
})

watch(products, (val) => {
  if (import.meta.client) localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
}, { deep: true })

watch(perRow, (val) => {
  if (import.meta.client) localStorage.setItem(PERROW_KEY, String(val))
})

watch(jitter, (val) => {
  if (import.meta.client) localStorage.setItem(JITTER_KEY, String(val))
})

watch(minObs, (val) => {
  if (import.meta.client) localStorage.setItem(MINOBS_KEY, String(val))
})

const addedIds = computed(() => new Set(products.value.map(p => p.id)))

// Instant client-side search: keep products above the min-obs threshold, then
// match the typed query; with no query it lists the most-observed products.
const searchResults = computed(() => {
  const q = query.value.trim().toLowerCase()
  return allProducts.value
    .filter(p => (p.obs ?? 0) >= minObs.value)
    .filter(p => !q || p.name.toLowerCase().includes(q))
    .slice(0, 12)
})

function addProduct(product: ProductHit) {
  if (!addedIds.value.has(product.id)) products.value.push(product)
  query.value = ''
  focused.value = false
}

function removeProduct(id: string) {
  products.value = products.value.filter(p => p.id !== id)
}

function onSearchBlur() {
  // delay so a click on a result registers before the dropdown closes
  setTimeout(() => { focused.value = false }, 150)
}

// Keyboard navigation of the search dropdown.
const highlightedIndex = ref(0)
const dropdownEl = ref<HTMLElement | null>(null)

watch(searchResults, () => { highlightedIndex.value = 0 })
watch(highlightedIndex, (i) => {
  nextTick(() => {
    const el = dropdownEl.value?.children?.[i] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  })
})

function onSearchKeydown(e: KeyboardEvent) {
  const n = searchResults.value.length
  if (!focused.value || !n) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    highlightedIndex.value = (highlightedIndex.value + 1) % n
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    highlightedIndex.value = (highlightedIndex.value - 1 + n) % n
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const p = searchResults.value[highlightedIndex.value]
    if (p && !addedIds.value.has(p.id)) addProduct(p)
  } else if (e.key === 'Tab') {
    // autocomplete the box to the highlighted product's name
    const p = searchResults.value[highlightedIndex.value]
    if (p && query.value.trim() && p.name !== query.value) {
      e.preventDefault()
      query.value = p.name
    }
  } else if (e.key === 'Escape') {
    focused.value = false
    ;(e.target as HTMLElement).blur()
  }
}

// ── drag-and-drop reorder ───────────────────────────────────────────────
// The card's grip handle is the only draggable element, so its native
// dragstart bubbles here; the canvas stays non-draggable (box-zoom intact).
const dragFromIndex = ref<number | null>(null)

function onDragStart(i: number, e: DragEvent) {
  dragFromIndex.value = i
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    const cell = (e.target as HTMLElement | null)?.closest('.chart-cell') as HTMLElement | null
    if (cell) e.dataTransfer.setDragImage(cell, 24, 24)
  }
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}

function onDrop(toIndex: number) {
  const from = dragFromIndex.value
  if (from === null || from === toIndex) return
  const arr = [...products.value]
  const [moved] = arr.splice(from, 1)
  arr.splice(toIndex, 0, moved)
  products.value = arr
}

function onDragEnd() {
  dragFromIndex.value = null
}
</script>

<template>
  <UContainer class="py-8 max-w-7xl">
    <div class="mb-6">
      <h1 class="text-2xl font-bold mb-1">
        Price History
      </h1>
      <p class="text-muted text-sm">
        Add a chart per product to compare price trends across stores. Drag the grip to reorder; your layout is saved in this browser.
      </p>
    </div>

    <div class="flex flex-col lg:flex-row gap-6 items-start">
      <!-- filters sidebar -->
      <aside class="w-full lg:w-72 shrink-0 space-y-5 lg:sticky lg:top-24">
        <div class="relative">
          <UInput
            v-model="query"
            placeholder="Search or browse products…"
            icon="i-lucide-search"
            class="w-full"
            @focus="focused = true"
            @blur="onSearchBlur"
            @keydown="onSearchKeydown"
          />
          <div
            v-if="focused && searchResults.length"
            ref="dropdownEl"
            class="absolute z-20 w-full mt-1 bg-default border border-default rounded-lg shadow-lg overflow-hidden max-h-96 overflow-y-auto"
          >
            <button
              v-for="(product, i) in searchResults"
              :key="product.id"
              class="w-full text-left px-3 py-2 flex items-center gap-2 transition-colors disabled:opacity-50"
              :class="i === highlightedIndex ? 'bg-elevated' : ''"
              :disabled="addedIds.has(product.id)"
              @mouseenter="highlightedIndex = i"
              @click="addProduct(product)"
            >
              <UIcon name="i-lucide-package" class="text-muted shrink-0" />
              <span class="truncate">{{ product.name }}</span>
              <UBadge color="neutral" variant="subtle" size="sm" class="ml-auto shrink-0">
                {{ product.obs }} obs
              </UBadge>
              <UIcon
                v-if="addedIds.has(product.id)"
                name="i-lucide-check"
                class="text-primary shrink-0"
              />
            </button>
          </div>
        </div>

        <div>
          <label class="block text-xs text-muted mb-1">Min. observations</label>
          <UInput
            v-model.number="minObs"
            type="number"
            :min="0"
            class="w-full"
          />
        </div>

        <div class="flex items-center justify-between">
          <span class="text-sm text-muted">Jitter dots</span>
          <USwitch v-model="jitter" size="sm" />
        </div>

        <div class="flex items-center justify-between">
          <span class="text-sm text-muted">Charts per row</span>
          <UButtonGroup size="xs">
            <UButton
              v-for="n in [1, 2, 3]"
              :key="n"
              :variant="perRow === n ? 'solid' : 'outline'"
              color="neutral"
              @click="perRow = n"
            >
              {{ n }}
            </UButton>
          </UButtonGroup>
        </div>
      </aside>

      <!-- charts -->
      <div class="flex-1 min-w-0 w-full">
        <div
          v-if="products.length"
          class="grid gap-6"
          :style="{ gridTemplateColumns: `repeat(${perRow}, minmax(0, 1fr))` }"
        >
          <div
            v-for="(product, i) in products"
            :key="product.id"
            class="chart-cell transition-opacity"
            :class="{ 'opacity-40': dragFromIndex === i }"
            @dragstart="onDragStart(i, $event)"
            @dragend="onDragEnd"
            @dragover="onDragOver"
            @drop="onDrop(i)"
          >
            <ProductChart
              :product="product"
              :jitter="jitter"
              @remove="removeProduct(product.id)"
            />
          </div>
        </div>

        <div
          v-else
          class="text-center py-16 text-muted border border-dashed border-default rounded-xl"
        >
          <UIcon name="i-lucide-line-chart" class="text-4xl mb-2" />
          <p>Search or browse in the sidebar to add your first chart.</p>
        </div>
      </div>
    </div>
  </UContainer>
</template>
