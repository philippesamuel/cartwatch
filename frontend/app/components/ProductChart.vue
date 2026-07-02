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
  jitter?: boolean
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

function median(nums: number[]) {
  const s = [...nums].sort((a, b) => a - b)
  const mid = Math.floor(s.length / 2)
  return s.length % 2 ? s[mid]! : (s[mid - 1]! + s[mid]!) / 2
}
function startOfMonth(ts: number) {
  const d = new Date(ts)
  return new Date(d.getFullYear(), d.getMonth(), 1).getTime()
}
const JITTER_MS = 4 * 24 * 60 * 60 * 1000 // spread same-day dots by up to ±4 days

// Two datasets per chain: the raw observations as dots, plus a solid line
// through the monthly median. Every raw observation stays visible.
const chartData = computed(() => {
  const chains = [...new Set(history.value.map(p => p.store_chain))]
  const datasets: any[] = []
  for (const chain of chains) {
    const color = CHAIN_COLORS[chain] ?? '#94a3b8'
    const points = history.value.filter(p => p.store_chain === chain)

    // raw dots — optionally jittered on the date axis to reveal same-day overlaps
    datasets.push({
      label: `${chain} (raw)`,
      data: points.map((p) => {
        const base = new Date(p.date).getTime()
        const x = props.jitter ? base + (Math.random() * 2 - 1) * JITTER_MS : base
        return { x, y: p.unit_price, meta: p }
      }),
      showLine: false,
      pointRadius: 3,
      pointHoverRadius: 6,
      pointBackgroundColor: color,
      borderColor: color
    })

    // monthly-median line — dashed + diamond markers = "this is calculated"
    const byMonth = new Map<number, number[]>()
    for (const p of points) {
      const key = startOfMonth(new Date(p.date).getTime())
      const arr = byMonth.get(key) ?? []
      arr.push(p.unit_price)
      byMonth.set(key, arr)
    }
    const line = [...byMonth.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([x, prices]) => ({ x, y: median(prices), agg: true }))
    datasets.push({
      label: chain,
      data: line,
      borderColor: color,
      backgroundColor: color + '33',
      borderWidth: 2,
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 0
    })
  }
  return { datasets }
})

// ── zoom / pan ──────────────────────────────────────────────────────────
const chartRef = ref<{ chart?: import('chart.js').Chart }>()

function zoomIn() {
  chartRef.value?.chart?.zoom(1.2)
}
function zoomOut() {
  chartRef.value?.chart?.zoom(0.8)
}
function resetZoom() {
  chartRef.value?.chart?.resetZoom()
}

// Custom box zoom with an axis-matching preview: a mostly-horizontal drag locks
// to X (full-height band), a mostly-vertical drag to Y (full-width band), and a
// square-ish drag zooms both. An explicit X/Y toggle overrides the auto choice.
// Done by hand (the plugin's own drag is disabled) so the preview band always
// matches what actually gets zoomed.
type Pt = { x: number; y: number }
type BoxStyle = { left: string; top: string; width: string; height: string; background: string; border: string }
const boxStyle = ref<BoxStyle | null>(null)
let boxStart: Pt | null = null
const MIN_DRAG = 8 // px — below this it's a click, not a zoom
const DOMINANCE = 2 // one axis must be this many times longer to lock to it

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v))
}
function pointerPos(e: MouseEvent): Pt | null {
  const chart = chartRef.value?.chart
  if (!chart) return null
  const rect = chart.canvas.getBoundingClientRect()
  const ca = chart.chartArea
  return {
    x: clamp(e.clientX - rect.left, ca.left, ca.right),
    y: clamp(e.clientY - rect.top, ca.top, ca.bottom)
  }
}
function boxMode(dx: number, dy: number): 'x' | 'y' | 'xy' {
  // Axis is chosen by the drag shape: mostly-horizontal → x, mostly-vertical → y.
  if (dx < MIN_DRAG && dy < MIN_DRAG) return 'xy'
  if (dx >= dy * DOMINANCE) return 'x'
  if (dy >= dx * DOMINANCE) return 'y'
  return 'xy'
}
function onBoxDown(e: MouseEvent) {
  if (e.shiftKey) return // shift-drag pans
  boxStart = pointerPos(e)
  boxStyle.value = null
}
function onBoxMove(e: MouseEvent) {
  const chart = chartRef.value?.chart
  const p = pointerPos(e)
  if (!boxStart || !chart || !p) return
  const ca = chart.chartArea
  const dx = Math.abs(p.x - boxStart.x)
  const dy = Math.abs(p.y - boxStart.y)
  const mode = boxMode(dx, dy)
  let left: number, top: number, width: number, height: number
  if (mode === 'x') {
    left = Math.min(boxStart.x, p.x); width = dx; top = ca.top; height = ca.bottom - ca.top
  } else if (mode === 'y') {
    top = Math.min(boxStart.y, p.y); height = dy; left = ca.left; width = ca.right - ca.left
  } else {
    left = Math.min(boxStart.x, p.x); top = Math.min(boxStart.y, p.y); width = dx; height = dy
  }
  boxStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    background: 'rgba(34,197,94,0.15)',
    border: '1px solid rgba(34,197,94,0.7)'
  }
}
function onBoxUp(e: MouseEvent) {
  const start = boxStart
  boxStart = null
  boxStyle.value = null
  const chart = chartRef.value?.chart
  const p = pointerPos(e)
  if (!start || !chart || !p) return
  const dx = Math.abs(p.x - start.x)
  const dy = Math.abs(p.y - start.y)
  if (dx < MIN_DRAG && dy < MIN_DRAG) return // a click, not a zoom
  const mode = boxMode(dx, dy)
  const z = chart as unknown as { zoomScale: (id: string, range: { min: number; max: number }, t: string) => void }
  if (mode === 'x' || mode === 'xy') {
    const a = chart.scales.x.getValueForPixel(Math.min(start.x, p.x))!
    const b = chart.scales.x.getValueForPixel(Math.max(start.x, p.x))!
    z.zoomScale('x', { min: Math.min(a, b), max: Math.max(a, b) }, 'none')
  }
  if (mode === 'y' || mode === 'xy') {
    const a = chart.scales.y.getValueForPixel(Math.min(start.y, p.y))!
    const b = chart.scales.y.getValueForPixel(Math.max(start.y, p.y))!
    z.zoomScale('y', { min: Math.min(a, b), max: Math.max(a, b) }, 'none')
  }
}
function cancelBox() {
  boxStart = null
  boxStyle.value = null
}

// Grab cursor: hint pan-ability on Shift-hover, show a closed fist while panning.
let shiftHeld = false
let panning = false
let hovering = false
function applyCursor() {
  const canvas = chartRef.value?.chart?.canvas
  if (!canvas) return
  canvas.style.cursor = panning
    ? 'grabbing'
    : hovering && shiftHeld
      ? 'grab'
      : hovering
        ? 'crosshair'
        : ''
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
  cancelBox()
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
    legend: {
      position: 'bottom' as const,
      labels: { filter: (item: any) => !item.text.endsWith('(raw)') }
    },
    tooltip: {
      callbacks: {
        title: (items: any[]) => {
          const raw = items[0]?.raw
          if (raw?.meta) return raw.meta.raw_name
          if (raw?.agg) return new Date(raw.x).toLocaleDateString(undefined, { year: 'numeric', month: 'long' })
          return ''
        },
        label: (ctx: any) => {
          const raw = ctx.raw
          const unit = displayUnit.value ?? raw?.meta?.item_unit
          const price = `${currencySymbol.value}${ctx.parsed.y.toFixed(2)}${unit ? ` / ${unit}` : ''}`
          if (raw?.meta) return `${ctx.dataset.label}: ${price}`
          if (raw?.agg) return `${ctx.dataset.label} · monthly median: ${price}`
          return ''
        },
        afterLabel: (ctx: any) => {
          const m = ctx.raw?.meta as PricePoint | undefined
          if (!m) return []
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
        mode: 'xy' as const,
        modifierKey: 'shift' as const,
        onPanStart: () => { panning = true; applyCursor() },
        onPanComplete: () => { panning = false; applyCursor() }
      },
      zoom: {
        wheel: { enabled: true },
        pinch: { enabled: false },
        // Box zoom is handled manually (onBoxDown/Move/Up) so the preview band
        // matches the locked axis; the plugin still owns wheel + pan.
        drag: { enabled: false },
        mode: 'xy' as const
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
        <div
          class="drag-handle cursor-grab active:cursor-grabbing text-muted hover:text-default shrink-0 flex items-center"
          draggable="true"
          aria-label="Drag to reorder"
          title="Drag to reorder"
        >
          <UIcon name="i-lucide-grip-vertical" />
        </div>
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
        class="relative h-72"
        @mouseenter="onChartEnter"
        @mouseleave="onChartLeave"
        @dblclick="resetZoom"
        @mousedown="onBoxDown"
        @mousemove="onBoxMove"
        @mouseup="onBoxUp"
      >
        <Line ref="chartRef" :data="chartData" :options="chartOptions" />
        <div
          v-if="boxStyle"
          class="absolute pointer-events-none rounded-sm"
          :style="boxStyle"
        />
      </div>
      <p class="text-xs text-muted mt-2 text-center">
        Scroll to zoom · drag a box (thin → one axis) · double-click to reset · shift-drag to pan
      </p>
    </div>
  </UCard>
</template>
