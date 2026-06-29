<script setup lang="ts">
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import { Line } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale)

useSeoMeta({ title: 'Price History · cartwatch' })

const supabase = useSupabaseClient()

type ProductHit = { id: string; name: string; short_name: string; unit: string | null }

const query = ref('')
const selectedProduct = ref<ProductHit | null>(null)
const searchResults = ref<ProductHit[]>([])
const searching = ref(false)
const loadingHistory = ref(false)

type PricePoint = {
  date: string
  unit_price: number
  store_chain: string
  raw_name: string
  quantity: number
  item_unit: string
  currency: string
}
const history = ref<PricePoint[]>([])

const CHAIN_COLORS: Record<string, string> = {
  REWE: '#e2001a',
  Lidl: '#0050aa',
  'Aldi Süd': '#00519e',
  'Aldi Nord': '#003087',
  Edeka: '#f5a800',
  Penny: '#c8102e',
  Netto: '#ffd100',
  Kaufland: '#e2001a',
  dm: '#d40511',
  Rossmann: '#e2001a',
  Amazon: '#ff9900',
  Other: '#94a3b8'
}

const CURRENCY_SYMBOLS: Record<string, string> = { EUR: '€', USD: '$', GBP: '£' }

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

async function selectProduct(product: ProductHit) {
  selectedProduct.value = product
  query.value = product.name
  searchResults.value = []
  await loadHistory(product.id)
}

async function loadHistory(productId: string) {
  loadingHistory.value = true
  history.value = []

  const { data } = await supabase
    .from('receipt_items')
    .select(`
      raw_name,
      quantity,
      unit_price,
      units ( symbol ),
      receipts!inner (
        purchased_at,
        currency,
        stores!inner (
          store_chains!inner ( name )
        )
      )
    `)
    .eq('canonical_product_id', productId)
    .order('receipts(purchased_at)', { ascending: true })

  if (data) {
    history.value = data.map((row: any) => ({
      date: row.receipts.purchased_at,
      unit_price: row.unit_price,
      store_chain: row.receipts.stores.store_chains.name,
      raw_name: row.raw_name,
      quantity: row.quantity,
      item_unit: row.units?.symbol ?? '',
      currency: row.receipts.currency
    }))
  }
  loadingHistory.value = false
}

const currencySymbol = computed(() => {
  const c = history.value[0]?.currency ?? 'EUR'
  return CURRENCY_SYMBOLS[c] ?? `${c} `
})

// Distinct units actually present across the receipt items for this product.
const distinctUnits = computed(() =>
  [...new Set(history.value.map(p => p.item_unit).filter(Boolean))]
)

// Prefer the canonical product's unit; fall back to the item unit only when unambiguous.
const displayUnit = computed(() =>
  selectedProduct.value?.unit ?? (distinctUnits.value.length === 1 ? distinctUnits.value[0]! : null)
)

// True when there's no canonical unit and items disagree — prices aren't comparable yet.
const unitsMixed = computed(() =>
  !selectedProduct.value?.unit && distinctUnits.value.length > 1
)

const yAxisLabel = computed(() =>
  `Price (${currencySymbol.value}${displayUnit.value ? ` / ${displayUnit.value}` : ''})`
)

const chartData = computed(() => {
  const chains = [...new Set(history.value.map(p => p.store_chain))]
  return {
    datasets: chains.map(chain => ({
      label: chain,
      data: history.value
        .filter(p => p.store_chain === chain)
        .map(p => ({ x: new Date(p.date).getTime(), y: p.unit_price, meta: p })),
      borderColor: CHAIN_COLORS[chain] ?? '#94a3b8',
      backgroundColor: (CHAIN_COLORS[chain] ?? '#94a3b8') + '33',
      tension: 0.3,
      pointRadius: 4,
      pointHoverRadius: 6
    }))
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'nearest' as const, intersect: true },
  scales: {
    x: {
      type: 'time' as const,
      time: { unit: 'month' as const },
      title: { display: true, text: 'Date' }
    },
    y: {
      title: { display: true, text: yAxisLabel.value },
      ticks: { callback: (v: any) => `${currencySymbol.value}${Number(v).toFixed(2)}` }
    }
  },
  plugins: {
    legend: { position: 'bottom' as const },
    tooltip: {
      callbacks: {
        // Full original receipt name as the tooltip heading.
        title: (items: any[]) => items[0]?.raw?.meta?.raw_name ?? '',
        label: (ctx: any) => {
          const m = ctx.raw.meta as PricePoint
          const unit = displayUnit.value ?? m.item_unit
          return `${ctx.dataset.label}: ${currencySymbol.value}${ctx.parsed.y.toFixed(2)}${unit ? ` / ${unit}` : ''}`
        },
        afterLabel: (ctx: any) => {
          const m = ctx.raw.meta as PricePoint
          const date = new Date(m.date).toLocaleDateString()
          const qty = `Qty: ${m.quantity}${m.item_unit ? ` ${m.item_unit}` : ''}`
          return [qty, date]
        }
      }
    }
  }
}))
</script>

<template>
  <UContainer class="py-8 max-w-4xl">
    <div class="mb-6">
      <h1 class="text-2xl font-bold mb-1">
        Price History
      </h1>
      <p class="text-muted text-sm">
        Search for a product to see how its price has evolved across stores.
      </p>
    </div>

    <div class="relative mb-8">
      <UInput
        v-model="query"
        placeholder="Search products… e.g. milk, eggs"
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
          class="w-full text-left px-4 py-2.5 hover:bg-elevated flex items-center gap-3 transition-colors"
          @click="selectProduct(product)"
        >
          <UIcon name="i-lucide-package" class="text-muted shrink-0" />
          <span>{{ product.name }}</span>
          <span class="text-muted text-sm ml-auto">{{ product.short_name }}</span>
        </button>
      </div>
    </div>

    <div v-if="loadingHistory" class="flex justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="animate-spin text-3xl text-muted" />
    </div>

    <template v-else-if="selectedProduct && history.length">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <UBadge variant="subtle">
          {{ history.length }} data points
        </UBadge>
        <span class="text-muted text-sm">for <strong>{{ selectedProduct.name }}</strong></span>
        <UBadge
          v-if="displayUnit && !unitsMixed"
          color="neutral"
          variant="outline"
        >
          {{ currencySymbol }} / {{ displayUnit }}
        </UBadge>
        <UBadge
          v-if="unitsMixed"
          color="warning"
          variant="subtle"
          icon="i-lucide-triangle-alert"
        >
          Mixed units: {{ distinctUnits.join(', ') }} — prices not comparable
        </UBadge>
      </div>
      <div class="h-80 border border-default rounded-xl p-4 bg-background">
        <Line :data="chartData" :options="chartOptions" />
      </div>
    </template>

    <div
      v-else-if="selectedProduct && !loadingHistory"
      class="text-center py-16 text-muted"
    >
      <UIcon name="i-lucide-inbox" class="text-4xl mb-2" />
      <p>No price history found for <strong>{{ selectedProduct.name }}</strong>.</p>
    </div>

    <div v-else-if="!selectedProduct" class="text-center py-16 text-muted">
      <UIcon name="i-lucide-trending-up" class="text-4xl mb-2" />
      <p>Search for a product above to see its price history.</p>
    </div>
  </UContainer>
</template>
