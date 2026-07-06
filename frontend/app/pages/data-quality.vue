<script setup lang="ts">
useSeoMeta({ title: 'Data Quality · cartwatch' })

const supabase = useSupabaseClient()

const euro = (v: any) => (v == null || v === '' ? '—' : `${Number(v) < 0 ? '-' : ''}€${Math.abs(Number(v)).toFixed(2)}`)

function groupByCount(arr: any[], key: string) {
  const m = new Map<string, number>()
  for (const x of arr) {
    const k = x[key] ?? '—'
    m.set(k, (m.get(k) ?? 0) + 1)
  }
  return [...m.entries()]
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => b.count - a.count)
}

type CheckResult = {
  count: number
  rows: Record<string, any>[]
  columns: { key: string; label: string; numeric?: boolean; format?: (v: any) => string }[]
  note?: string
}

type Check = {
  id: string
  title: string
  description: string
  severity: 'high' | 'medium' | 'low'
  run: () => Promise<CheckResult>
}

const checks: Check[] = [
  {
    id: 'unmatched-items',
    title: 'Unmatched receipt items',
    description: 'Line items not linked to any canonical product — excluded from price stats.',
    severity: 'high',
    run: async () => {
      const { data, count } = await supabase
        .from('receipt_items')
        .select('raw_name', { count: 'exact' })
        .is('ignore', null)
        .is('canonical_product_id', null)
      const grouped = groupByCount(data ?? [], 'raw_name')
      return {
        count: count ?? 0,
        rows: grouped.map(g => ({ name: g.value, n: g.count })),
        columns: [
          { key: 'name', label: 'Raw name' },
          { key: 'n', label: 'Occurrences', numeric: true }
        ],
        note: `Grouped by raw name · ${grouped.length} distinct names.`
      }
    }
  },
  {
    id: 'mixed-units',
    title: 'Products with mixed units',
    description: 'Same product recorded in more than one unit — prices are not comparable.',
    severity: 'high',
    run: async () => {
      const { data } = await supabase
        .from('mv_product_stats')
        .select('canonical_product_name, unit_symbol, line_item_count')
      const byName = new Map<string, Map<string, number>>()
      for (const r of data ?? []) {
        if (!r.unit_symbol) continue // a missing unit is its own check
        const units = byName.get(r.canonical_product_name) ?? new Map<string, number>()
        units.set(r.unit_symbol, (units.get(r.unit_symbol) ?? 0) + Number(r.line_item_count))
        byName.set(r.canonical_product_name, units)
      }
      const rows = [...byName.entries()]
        .filter(([, units]) => units.size > 1)
        .map(([name, units]) => ({
          name,
          units: [...units.entries()].map(([u, c]) => `${u} (${c})`).join(', '),
          n: units.size
        }))
        .sort((a, b) => b.n - a.n)
      return {
        count: rows.length,
        rows,
        columns: [
          { key: 'name', label: 'Product' },
          { key: 'units', label: 'Units (observations)' }
        ]
      }
    }
  },
  {
    id: 'bad-price',
    title: 'Items with invalid prices',
    description: 'Line items with a missing, zero, or negative price.',
    severity: 'high',
    run: async () => {
      const { data, count } = await supabase
        .from('receipt_items')
        .select('raw_name, unit_price, total_price', { count: 'exact' })
        .is('ignore', null)
        .or('unit_price.is.null,unit_price.lte.0,total_price.is.null')
      return {
        count: count ?? 0,
        rows: data ?? [],
        columns: [
          { key: 'raw_name', label: 'Raw name' },
          { key: 'unit_price', label: 'Unit', numeric: true, format: euro },
          { key: 'total_price', label: 'Total', numeric: true, format: euro }
        ]
      }
    }
  },
  {
    id: 'total-mismatch',
    title: 'Receipt total mismatches',
    description: 'Receipts whose line items do not sum to the recorded total.',
    severity: 'high',
    run: async () => {
      const { data } = await supabase
        .from('receipts')
        .select('purchased_at, total, receipt_items(total_price)')
        .is('receipt_items(ignore)', null)
      const rows: Record<string, any>[] = []
      for (const r of data ?? []) {
        const sum = (r.receipt_items ?? []).reduce((s: number, i: any) => s + Number(i.total_price || 0), 0)
        const diff = Number(r.total) - sum
        if (Math.abs(diff) > 0.02) {
          rows.push({
            date: new Date(r.purchased_at).toLocaleDateString(),
            total: Number(r.total),
            items: sum,
            diff
          })
        }
      }
      rows.sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff))
      return {
        count: rows.length,
        rows,
        columns: [
          { key: 'date', label: 'Date' },
          { key: 'total', label: 'Recorded', numeric: true, format: euro },
          { key: 'items', label: 'Items sum', numeric: true, format: euro },
          { key: 'diff', label: 'Diff', numeric: true, format: euro }
        ]
      }
    }
  },
  {
    id: 'pending-matches',
    title: 'Pending product matches',
    description: 'Items in the reconciliation queue awaiting confirmation.',
    severity: 'medium',
    run: async () => {
      const { data, count } = await supabase
        .from('product_matches')
        .select('confidence, matched_by, receipt_items(raw_name), canonical_products(name)', { count: 'exact' })
        .eq('status', 'pending')
        .order('confidence', { ascending: true })
        .limit(200)
      return {
        count: count ?? 0,
        rows: (data ?? []).map((r: any) => ({
          raw: r.receipt_items?.raw_name ?? '—',
          suggestion: r.canonical_products?.name ?? '(no match)',
          confidence: r.confidence,
          by: r.matched_by
        })),
        columns: [
          { key: 'raw', label: 'Raw name' },
          { key: 'suggestion', label: 'Suggested' },
          { key: 'confidence', label: 'Confidence', numeric: true, format: v => Number(v).toFixed(2) },
          { key: 'by', label: 'By' }
        ],
        note: 'Sorted by lowest confidence first.'
      }
    }
  },
  {
    id: 'items-no-unit',
    title: 'Items without a unit',
    description: 'Receipt line items missing a unit symbol.',
    severity: 'medium',
    run: async () => {
      const { data, count } = await supabase
        .from('receipt_items')
        .select('raw_name', { count: 'exact' })
        .is('ignore', null)
        .is('unit_id', null)
      const grouped = groupByCount(data ?? [], 'raw_name')
      return {
        count: count ?? 0,
        rows: grouped.map(g => ({ name: g.value, n: g.count })),
        columns: [
          { key: 'name', label: 'Raw name' },
          { key: 'n', label: 'Occurrences', numeric: true }
        ]
      }
    }
  },
  {
    id: 'products-no-category',
    title: 'Products without a category',
    description: 'Canonical products not assigned to a category.',
    severity: 'low',
    run: async () => {
      const { data, count } = await supabase
        .from('canonical_products')
        .select('name, short_name', { count: 'exact' })
        .is('category_id', null)
        .order('name')
      return {
        count: count ?? 0,
        rows: data ?? [],
        columns: [
          { key: 'name', label: 'Product' },
          { key: 'short_name', label: 'Short name' }
        ]
      }
    }
  },
  {
    id: 'stores-no-chain',
    title: 'Stores without a chain',
    description: 'Stores not linked to a retailer chain.',
    severity: 'low',
    run: async () => {
      const { data, count } = await supabase
        .from('stores')
        .select('name, city', { count: 'exact' })
        .is('ignore', null)
        .is('chain_id', null)
        .order('name')
      return {
        count: count ?? 0,
        rows: data ?? [],
        columns: [
          { key: 'name', label: 'Store' },
          { key: 'city', label: 'City' }
        ]
      }
    }
  }
]

type State = { count: number | null; rows: any[]; columns: any[]; note?: string; loading: boolean }
const state = reactive<Record<string, State>>(
  Object.fromEntries(checks.map(c => [c.id, { count: null, rows: [], columns: [], loading: true }]))
)

onMounted(() => {
  for (const c of checks) {
    c.run()
      .then((res) => {
        state[c.id] = { ...res, loading: false }
      })
      .catch((err) => {
        console.error(`[data-quality] ${c.id} failed`, err)
        state[c.id].loading = false
      })
  }
})

const anyLoading = computed(() => checks.some(c => state[c.id].loading))
const flaggedCount = computed(() => checks.filter(c => (state[c.id].count ?? 0) > 0).length)
</script>

<template>
  <UContainer class="py-8 max-w-4xl">
    <div class="mb-6">
      <h1 class="text-2xl font-bold mb-1">
        Data Quality
      </h1>
      <p class="text-muted text-sm">
        Issues that affect the accuracy of the dashboards. Expand a card to see the affected records.
      </p>
    </div>

    <div class="mb-5 flex items-center gap-2 text-sm">
      <UIcon v-if="anyLoading" name="i-lucide-loader-circle" class="animate-spin text-muted" />
      <template v-else-if="flaggedCount === 0">
        <UIcon name="i-lucide-circle-check" class="text-success" />
        <span>All {{ checks.length }} checks passed.</span>
      </template>
      <template v-else>
        <UIcon name="i-lucide-triangle-alert" class="text-warning" />
        <span><strong>{{ flaggedCount }}</strong> of {{ checks.length }} checks flagged issues.</span>
      </template>
    </div>

    <div class="space-y-3">
      <DataQualityCard
        v-for="c in checks"
        :key="c.id"
        :title="c.title"
        :description="c.description"
        :severity="c.severity"
        :count="state[c.id].count"
        :loading="state[c.id].loading"
        :rows="state[c.id].rows"
        :columns="state[c.id].columns"
        :note="state[c.id].note"
      />
    </div>
  </UContainer>
</template>
