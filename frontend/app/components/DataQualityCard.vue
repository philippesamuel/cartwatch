<script setup lang="ts">
type Column = { key: string; label: string; numeric?: boolean; format?: (v: any) => string }

const props = defineProps<{
  title: string
  description: string
  severity: 'high' | 'medium' | 'low'
  count: number | null
  loading: boolean
  rows: Record<string, any>[]
  columns: Column[]
  note?: string
}>()

const open = ref(false)
const MAX = 50

const SEV = {
  high: { badge: 'error' as const, icon: 'i-lucide-circle-alert', iconClass: 'text-error' },
  medium: { badge: 'warning' as const, icon: 'i-lucide-triangle-alert', iconClass: 'text-warning' },
  low: { badge: 'neutral' as const, icon: 'i-lucide-info', iconClass: 'text-muted' }
}

const clean = computed(() => props.count === 0)
const visibleRows = computed(() => props.rows.slice(0, MAX))
</script>

<template>
  <div class="border border-default rounded-xl overflow-hidden">
    <button
      class="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors"
      :class="clean ? 'cursor-default' : 'hover:bg-elevated/50'"
      :disabled="clean || loading"
      @click="open = !open"
    >
      <UIcon
        :name="clean ? 'i-lucide-circle-check' : SEV[severity].icon"
        class="text-lg shrink-0"
        :class="clean ? 'text-success' : SEV[severity].iconClass"
      />
      <div class="min-w-0">
        <div class="font-semibold">
          {{ title }}
        </div>
        <p class="text-sm text-muted truncate">
          {{ description }}
        </p>
      </div>
      <div class="ml-auto flex items-center gap-3 shrink-0">
        <UIcon v-if="loading" name="i-lucide-loader-circle" class="animate-spin text-muted" />
        <template v-else>
          <UBadge v-if="clean" color="success" variant="subtle" icon="i-lucide-check">
            Clean
          </UBadge>
          <UBadge v-else-if="count === null" color="neutral" variant="subtle">
            —
          </UBadge>
          <UBadge v-else :color="SEV[severity].badge" variant="subtle">
            {{ new Intl.NumberFormat().format(count) }}
          </UBadge>
        </template>
        <UIcon
          v-if="!clean && !loading"
          :name="open ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
          class="text-muted"
        />
      </div>
    </button>

    <div v-if="open && !clean" class="border-t border-default">
      <div v-if="!rows.length" class="px-4 py-6 text-center text-muted text-sm">
        No detail rows available.
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-default bg-elevated/30">
              <th
                v-for="c in columns"
                :key="c.key"
                class="px-4 py-2 font-medium text-muted whitespace-nowrap"
                :class="c.numeric ? 'text-right' : 'text-left'"
              >
                {{ c.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in visibleRows"
              :key="i"
              class="border-b border-default last:border-0"
            >
              <td
                v-for="c in columns"
                :key="c.key"
                class="px-4 py-1.5 whitespace-nowrap"
                :class="c.numeric ? 'text-right tabular-nums' : 'text-left'"
              >
                {{ c.format ? c.format(row[c.key]) : (row[c.key] ?? '—') }}
              </td>
            </tr>
          </tbody>
        </table>
        <p
          v-if="rows.length > MAX"
          class="px-4 py-2 text-xs text-muted border-t border-default"
        >
          Showing {{ MAX }} of {{ new Intl.NumberFormat().format(rows.length) }}.
        </p>
        <p
          v-else-if="note"
          class="px-4 py-2 text-xs text-muted border-t border-default"
        >
          {{ note }}
        </p>
      </div>
    </div>
  </div>
</template>
