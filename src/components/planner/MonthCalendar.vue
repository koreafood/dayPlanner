<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

type ISODate = string

const props = defineProps<{ selectedDate: ISODate; selectedDayNote?: string }>()
const emit = defineEmits<{ (e: 'select', date: ISODate): void }>()

function toISODate(d: Date): ISODate {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

function daysInMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()
}

const cursor = ref(startOfMonth(new Date()))

const monthNotes = ref<Record<string, string>>({})

async function loadMonthNotes(d: Date) {
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  try {
    const r = await fetch(`/api/month-notes?year=${year}&month=${month}`)
    if (!r.ok) throw new Error('')
    const data = (await r.json()) as { notes?: Record<string, string> }
    monthNotes.value = data.notes ?? {}
  } catch {
    monthNotes.value = {}
  }
}

watch(
  () => props.selectedDate,
  (v) => {
    const d = new Date(v)
    if (Number.isNaN(d.getTime())) return
    cursor.value = startOfMonth(d)
  },
  { immediate: true }
)

watch(
  cursor,
  (d) => {
    loadMonthNotes(d)
  },
  { immediate: true }
)

watch(
  () => [props.selectedDate, props.selectedDayNote] as const,
  ([date, note]) => {
    if (!date) return
    const next = { ...monthNotes.value }
    if (note && note.trim()) next[date] = note
    else delete next[date]
    monthNotes.value = next
  }
)

const title = computed(() => {
  return `${cursor.value.getFullYear()}년 ${cursor.value.getMonth() + 1}월`
})

const cells = computed(() => {
  const first = startOfMonth(cursor.value)
  const firstWeekday = first.getDay()
  const total = daysInMonth(cursor.value)
  const arr: Array<{ key: string; day?: number; date?: ISODate; weekday?: number }> = []
  for (let i = 0; i < firstWeekday; i++) arr.push({ key: `e-${i}` })
  for (let day = 1; day <= total; day++) {
    const d = new Date(cursor.value.getFullYear(), cursor.value.getMonth(), day)
    arr.push({ key: `d-${day}`, day, date: toISODate(d), weekday: d.getDay() })
  }
  return arr
})

const today = toISODate(new Date())

function prevMonth() {
  cursor.value = startOfMonth(new Date(cursor.value.getFullYear(), cursor.value.getMonth() - 1, 1))
}

function nextMonth() {
  cursor.value = startOfMonth(new Date(cursor.value.getFullYear(), cursor.value.getMonth() + 1, 1))
}

const weekdays = ['일', '월', '화', '수', '목', '금', '토']
</script>

<template>
  <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
    <div class="mb-3 flex items-center justify-between">
      <div class="text-sm font-semibold text-zinc-100">달력</div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-200 hover:bg-zinc-800"
          @click="prevMonth"
        >
          <ChevronLeft class="h-4 w-4" />
        </button>
        <div class="min-w-[120px] text-center text-xs font-medium text-zinc-200">
          {{ title }}
        </div>
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-200 hover:bg-zinc-800"
          @click="nextMonth"
        >
          <ChevronRight class="h-4 w-4" />
        </button>
      </div>
    </div>

    <div class="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold text-zinc-400">
      <div v-for="w in weekdays" :key="w" class="py-1">{{ w }}</div>
    </div>

    <div class="mt-1 grid grid-cols-7 gap-1">
      <button
        v-for="c in cells"
        :key="c.key"
        type="button"
        class="relative h-9 rounded-lg text-xs"
        :class="[
          !c.date ? 'pointer-events-none' : 'border border-zinc-800 bg-zinc-900 text-zinc-200 hover:bg-zinc-800',
          c.date === today ? 'ring-1 ring-indigo-500/60' : '',
          c.date === selectedDate ? 'bg-indigo-600 text-white hover:bg-indigo-600' : '',
          c.weekday === 0 ? 'text-rose-300' : '',
          c.weekday === 6 ? 'text-sky-300' : '',
        ]"
        @click="c.date && emit('select', c.date)"
        :title="c.date && monthNotes[c.date] ? monthNotes[c.date] : ''"
      >
        <span v-if="c.day">{{ c.day }}</span>
        <span
          v-if="c.date && monthNotes[c.date]"
          class="pointer-events-none absolute bottom-1 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-sky-400"
        />
      </button>
    </div>

    <div class="mt-3 rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2">
      <div class="text-[11px] text-zinc-400">선택 날짜</div>
      <div class="text-sm font-semibold text-zinc-100">{{ selectedDate }}</div>
    </div>
  </section>
</template>
