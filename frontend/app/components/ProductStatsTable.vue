<script setup lang="ts">
const supabase = useSupabaseClient()

type Row = {
  canonical_product_name: string
  unit_symbol: string
  line_item_count: number
  receipt_count: number
  store_count: number
  retailer_count: number
  median_unit_price: number | null
  min_unit_price: number | null
  max_unit_price: number | null
  total_price_sum: number | null
}

const rows = ref<Row[]>([])
const loading = ref(true)

onMounted(async () => {
  const { data } = await supabase
    .from('mv_product_stats')
    .select('canonical_product_name, unit_symbol, line_item_count, receipt_count, store_count, retailer_count, median_unit_price, min_unit_price, max_unit_price, total_price_sum')
  rows.value = (data ?? []) as Row[]
  loading.value = false
})

function fmtPrice(v: number | null) {
  return v == null ? '—' : `€${Number(v).toFixed(2)}`
}
function fmtInt(v: number | null) {
  return v == null ? '—' : new Intl.NumberFormat().format(v)
}

type Col = {
  key: keyof Row
  label: string
  numeric: boolean
  title?: string
  format?: (r: Row) => string
}
const columns: Col[] = [
  { key: 'canonical_product_name', label: 'Product', numeric: false },
  { key: 'unit_symbol', label: 'Unit', numeric: false },
  { key: 'line_item_count', label: 'Obs.', numeric: true, title: 'Line items observed', format: r => fmtInt(r.line_item_count) },
  { key: 'receipt_count', label: 'Receipts', numeric: true, title: 'Distinct receipts', format: r => fmtInt(r.receipt_count) },
  { key: 'store_count', label: 'Stores', numeric: true, title: 'Distinct stores', format: r => fmtInt(r.store_count) },
  { key: 'retailer_count', label: 'Retailers', numeric: true, title: 'Distinct retailers', format: r => fmtInt(r.retailer_count) },
  { key: 'median_unit_price', label: 'Median', numeric: true, title: 'Median price per unit', format: r => fmtPrice(r.median_unit_price) },
  { key: 'min_unit_price', label: 'Min', numeric: true, title: 'Min price per unit', format: r => fmtPrice(r.min_unit_price) },
  { key: 'max_unit_price', label: 'Max', numeric: true, title: 'Max price per unit', format: r => fmtPrice(r.max_unit_price) },
  { key: 'total_price_sum', label: 'Total', numeric: true, title: 'Total spent', format: r => fmtPrice(r.total_price_sum) }
]

const query = ref('')
const unitFilter = ref('all')
const sortKey = ref<keyof Row>('line_item_count')
const sortDir = ref<'asc' | 'desc'>('desc')

const availableUnits = computed(() =>
  [...new Set(rows.value.map(r => r.unit_symbol).filter(Boolean))].sort()
)

function toggleSort(key: keyof Row) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    // text defaults to A→Z, numbers to high→low
    sortDir.value = key === 'canonical_product_name' || key === 'unit_symbol' ? 'asc' : 'desc'
  }
}

const filtered = computed(() => {
  const s = query.value.trim().toLowerCase()
  return rows.value.filter(r =>
    (unitFilter.value === 'all' || r.unit_symbol === unitFilter.value)
    && (!s || r.canonical_product_name.toLowerCase().includes(s))
  )
})

const sorted = computed(() => {
  const dir = sortDir.value === 'asc' ? 1 : -1
  const k = sortKey.value
  return [...filtered.value].sort((a, b) => {
    const av = a[k]
    const bv = b[k]
    if (typeof av === 'string' && typeof bv === 'string') return av.localeCompare(bv) * dir
    return (((av as number) ?? 0) - ((bv as number) ?? 0)) * dir
  })
})
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-3 flex-wrap">
      <UInput
        v-model="query"
        placeholder="Filter products…"
        icon="i-lucide-search"
        class="w-64"
      />
      <UButtonGroup size="xs">
        <UButton
          :variant="unitFilter === 'all' ? 'solid' : 'outline'"
          color="neutral"
          @click="unitFilter = 'all'"
        >
          All units
        </UButton>
        <UButton
          v-for="u in availableUnits"
          :key="u"
          :variant="unitFilter === u ? 'solid' : 'outline'"
          color="neutral"
          @click="unitFilter = u"
        >
          {{ u }}
        </UButton>
      </UButtonGroup>
      <span class="text-sm text-muted">
        {{ sorted.length }}<span v-if="sorted.length !== rows.length"> / {{ rows.length }}</span> products
      </span>
      <span class="text-xs text-muted ml-auto">
        Median / Min / Max are price per unit
      </span>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <UIcon name="i-lucide-loader-circle" class="animate-spin text-3xl text-muted" />
    </div>

    <div v-else class="overflow-x-auto border border-default rounded-xl">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-default bg-elevated/50">
            <th
              v-for="col in columns"
              :key="col.key"
              scope="col"
              :title="col.title"
              class="px-3 py-2.5 font-semibold text-muted whitespace-nowrap cursor-pointer select-none hover:text-default transition-colors"
              :class="col.numeric ? 'text-right' : 'text-left'"
              @click="toggleSort(col.key)"
            >
              <span class="inline-flex items-center gap-1" :class="col.numeric ? 'flex-row-reverse' : ''">
                {{ col.label }}
                <UIcon
                  v-if="sortKey === col.key"
                  :name="sortDir === 'asc' ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
                  class="size-3.5 text-primary"
                />
                <UIcon v-else name="i-lucide-chevrons-up-down" class="size-3.5 opacity-30" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in sorted"
            :key="row.canonical_product_name + row.unit_symbol"
            class="border-b border-default last:border-0 hover:bg-elevated/50 transition-colors"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              class="px-3 py-2 whitespace-nowrap"
              :class="[
                col.numeric ? 'text-right tabular-nums' : 'text-left',
                col.key === 'canonical_product_name' ? 'font-medium text-highlighted' : '',
                col.key === 'unit_symbol' ? 'text-muted' : ''
              ]"
            >
              {{ col.format ? col.format(row) : row[col.key] }}
            </td>
          </tr>
          <tr v-if="!sorted.length">
            <td :colspan="columns.length" class="px-3 py-10 text-center text-muted">
              No products match “{{ query }}”.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
