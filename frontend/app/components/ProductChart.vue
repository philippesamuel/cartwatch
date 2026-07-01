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
import zoomPlugin from 'chartjs-plugin-zoom'
import { Line } from 'vue-chartjs'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, TimeScale, zoomPlugin
)

const props = defineProps<{
  product: { id: string; name: string; short_name: string; unit: string | null }
}>()
defineEmits<{ remove: [] }>()

const supabase = useSupabaseClient()

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
const loading = ref(true)

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

async function loadHistory() {
  loading.value = true
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
    .eq('canonical_product_id', props.product.id)
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
  loading.value = false
}
onMounted(loadHistory)

const currencySymbol = computed(() => {
  const c = history.value[0]?.currency ?? 'EUR'
  return CURRENCY_SYMBOLS[c] ?? `${c} `
})

const distinctUnits = computed(() =>
  [...new Set(history.value.map(p => p.item_unit).filter(Boolean))]
)

const displayUnit = computed(() =>
  props.product.unit ?? (distinctUnits.value.length === 1 ? distinctUnits.value[0]! : null)
)

const unitsMixed = computed(() =>
  !props.product.unit && distinctUnits.value.length > 1
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

// ── zoom / pan ──────────────────────────────────────────────────────────
const chartRef = ref<{ chart?: import('chart.js').Chart }>()
const zoomMode = ref<'xy' | 'x' | 'y'>('xy')

function zoomIn() {
  chartRef.value?.chart?.zoom(1.2)
}
function zoomOut() {
  chartRef.value?.chart?.zoom(0.8)
}
function resetZoom() {
  chartRef.value?.chart?.resetZoom()
}

// Direction-aware box zoom: in XY mode the plugin zooms both axes to the drag
// box; afterwards we undo the axis that barely moved, so a flat drag zooms only
// X and a tall drag only Y. An explicit X/Y toggle wins. (The plugin caches its
// own mode, so we can't influence it live — hence the after-the-fact restore.)
let dragProbe: { x: number; y: number } | null = null
let dragVec = { dx: 0, dy: 0 }
let preX: { min: number; max: number } | null = null
let preY: { min: number; max: number } | null = null
function dragMode(): 'x' | 'y' | 'xy' {
  if (zoomMode.value !== 'xy') return zoomMode.value
  const { dx, dy } = dragVec
  const MIN = 12 // px — below this the drag is too small to have a direction
  const DOMINANCE = 2.5 // one axis must be this many times longer to lock to it
  if (dx < MIN && dy < MIN) return 'xy'
  if (dx >= dy * DOMINANCE) return 'x'
  if (dy >= dx * DOMINANCE) return 'y'
  return 'xy'
}
function onDragProbeDown(e: MouseEvent) {
  if (e.shiftKey) return // shift-drag pans, not zooms
  dragProbe = { x: e.clientX, y: e.clientY }
  dragVec = { dx: 0, dy: 0 }
  const chart = chartRef.value?.chart
  if (chart) {
    preX = { min: chart.scales.x.min, max: chart.scales.x.max }
    preY = { min: chart.scales.y.min, max: chart.scales.y.max }
  }
}
function onDragProbeMove(e: MouseEvent) {
  if (!dragProbe) return
  dragVec = { dx: Math.abs(e.clientX - dragProbe.x), dy: Math.abs(e.clientY - dragProbe.y) }
}
function onDragProbeUp() {
  if (!dragProbe) return
  dragProbe = null
  const m = dragMode()
  const chart = chartRef.value?.chart
  if (m === 'xy' || !chart || !preX || !preY) return
  const px = preX
  const py = preY
  // The drag zoom lands first; on the next frame reset the near-flat axis.
  requestAnimationFrame(() => {
    const z = chart as unknown as { zoomScale: (id: string, range: { min: number; max: number }, t: string) => void }
    if (m === 'x') z.zoomScale('y', { min: py.min, max: py.max }, 'none')
    else z.zoomScale('x', { min: px.min, max: px.max }, 'none')
  })
}

// Grab cursor: hint pan-ability on Shift-hover, show a closed fist while panning.
let shiftHeld = false
let panning = false
let hovering = false
function applyCursor() {
  const canvas = chartRef.value?.chart?.canvas
  if (!canvas) return
  canvas.style.cursor = panning ? 'grabbing' : (hovering && shiftHeld ? 'grab' : '')
}
function onShiftKey(e: KeyboardEvent) {
  if (e.key !== 'Shift') return
  shiftHeld = e.type === 'keydown'
  applyCursor()
}
function onChartEnter() {
  hovering = true
  applyCursor()
}
function onChartLeave() {
  hovering = false
  applyCursor()
}
onMounted(() => {
  window.addEventListener('keydown', onShiftKey)
  window.addEventListener('keyup', onShiftKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onShiftKey)
  window.removeEventListener('keyup', onShiftKey)
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
    },
    zoom: {
      // Hold Shift and drag to pan; plain drag draws a zoom box.
      pan: {
        enabled: true,
        mode: zoomMode.value,
        modifierKey: 'shift' as const,
        onPanStart: () => { panning = true; applyCursor() },
        onPanComplete: () => { panning = false; applyCursor() }
      },
      zoom: {
        wheel: { enabled: true },
        pinch: { enabled: false },
        drag: {
          enabled: true,
          backgroundColor: 'rgba(34,197,94,0.15)',
          borderColor: 'rgba(34,197,94,0.7)',
          borderWidth: 1
        },
        mode: zoomMode.value
      },
      limits: {
        x: { min: 'original' as const, max: 'original' as const },
        y: { min: 'original' as const, max: 'original' as const }
      }
    }
  }
}))
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center gap-2 min-w-0">
          <UIcon name="i-lucide-package" class="text-muted shrink-0" />
          <h3 class="font-semibold truncate">
            {{ product.name }}
          </h3>
          <UBadge v-if="!loading && history.length" variant="subtle" size="sm">
            {{ history.length }} pts
          </UBadge>
          <UBadge
            v-if="displayUnit && !unitsMixed"
            color="neutral"
            variant="outline"
            size="sm"
          >
            {{ currencySymbol }} / {{ displayUnit }}
          </UBadge>
          <UBadge
            v-if="unitsMixed"
            color="warning"
            variant="subtle"
            size="sm"
            icon="i-lucide-triangle-alert"
          >
            Mixed: {{ distinctUnits.join(', ') }}
          </UBadge>
        </div>

        <div class="flex items-center gap-1 ml-auto">
          <UButtonGroup size="xs">
            <UButton
              :variant="zoomMode === 'xy' ? 'solid' : 'outline'"
              color="neutral"
              @click="zoomMode = 'xy'"
            >
              XY
            </UButton>
            <UButton
              :variant="zoomMode === 'x' ? 'solid' : 'outline'"
              color="neutral"
              @click="zoomMode = 'x'"
            >
              X
            </UButton>
            <UButton
              :variant="zoomMode === 'y' ? 'solid' : 'outline'"
              color="neutral"
              @click="zoomMode = 'y'"
            >
              Y
            </UButton>
          </UButtonGroup>
          <UButton
            size="xs"
            color="neutral"
            variant="ghost"
            icon="i-lucide-zoom-in"
            aria-label="Zoom in"
            @click="zoomIn"
          />
          <UButton
            size="xs"
            color="neutral"
            variant="ghost"
            icon="i-lucide-zoom-out"
            aria-label="Zoom out"
            @click="zoomOut"
          />
          <UButton
            size="xs"
            color="neutral"
            variant="ghost"
            icon="i-lucide-rotate-ccw"
            aria-label="Reset zoom"
            @click="resetZoom"
          />
          <UButton
            size="xs"
            color="error"
            variant="ghost"
            icon="i-lucide-x"
            aria-label="Remove chart"
            @click="$emit('remove')"
          />
        </div>
      </div>
    </template>

    <div v-if="loading" class="flex justify-center items-center h-72">
      <UIcon name="i-lucide-loader-circle" class="animate-spin text-2xl text-muted" />
    </div>
    <div
      v-else-if="!history.length"
      class="flex flex-col items-center justify-center h-72 text-muted"
    >
      <UIcon name="i-lucide-inbox" class="text-3xl mb-2" />
      <p>No price history for <strong>{{ product.name }}</strong>.</p>
    </div>
    <div v-else>
      <div
        class="h-72"
        @mouseenter="onChartEnter"
        @mouseleave="onChartLeave"
        @dblclick="resetZoom"
        @mousedown="onDragProbeDown"
        @mousemove="onDragProbeMove"
        @mouseup="onDragProbeUp"
      >
        <Line ref="chartRef" :data="chartData" :options="chartOptions" />
      </div>
      <p class="text-xs text-muted mt-2 text-center">
        Scroll to zoom · drag to box-zoom · double-click to reset · shift-drag to pan
      </p>
    </div>
  </UCard>
</template>
