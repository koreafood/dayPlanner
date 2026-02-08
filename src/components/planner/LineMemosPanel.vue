<script setup lang="ts">
/*
  LineMemosPanel
  - 목적: 시간대별 일정 메모를 한 줄씩 입력/삭제하고 시간 선택을 제공
  - v-model:
    * scheduleMemos: ScheduleMemo[] (hour, text)
  - 이벤트:
    * add: 새로운 일정 항목 추가
    * remove(index): 해당 인덱스 항목 삭제
  - 로직:
    * setHour/setText: 불변 업데이트로 배열 갱신
    * onHourChange/onTextInput: 폼 이벤트 핸들링
*/
import { Plus, Trash2 } from 'lucide-vue-next'
import type { ScheduleMemo } from '@/composables/usePlanner'

const scheduleMemos = defineModel<ScheduleMemo[]>('scheduleMemos', { required: true })
const emit = defineEmits<{ (e: 'add'): void; (e: 'remove', index: number): void }>()

function setHour(idx: number, hour: number) {
  const next = scheduleMemos.value.slice()
  const it = next[idx]
  if (!it) return
  next[idx] = { ...it, hour }
  scheduleMemos.value = next
}

function setText(idx: number, text: string) {
  const next = scheduleMemos.value.slice()
  const it = next[idx]
  if (!it) return
  next[idx] = { ...it, text }
  scheduleMemos.value = next
}

function onHourChange(e: Event, idx: number) {
  const target = e.target as HTMLSelectElement | null
  const v = Number(target?.value ?? 0)
  setHour(idx, Number.isFinite(v) ? Math.max(0, Math.min(23, v)) : 0)
}

function onTextInput(e: Event, idx: number) {
  const target = e.target as HTMLInputElement | null
  setText(idx, target?.value ?? '')
}

const hours = Array.from({ length: 24 }, (_, i) => i)
</script>

<template>
  <!-- 일정 메모 패널 -->
  <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
    <div class="mb-3 flex items-center justify-between">
      <div class="text-sm font-semibold text-zinc-100">일정메모</div>
      <!-- 일정 추가 버튼 -->
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
        @click="emit('add')"
      >
        <Plus class="h-4 w-4" />
        일정 추가
      </button>
    </div>

    <!-- 일정 항목 리스트 -->
    <div class="space-y-2">
      <div
        v-for="(m, idx) in scheduleMemos"
        :key="idx + '-' + m.hour"
        class="flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2"
      >
        <div class="w-7 shrink-0 text-center text-[11px] font-semibold text-zinc-500">{{ idx + 1 }}</div>
        <!-- 시간 선택 -->
        <select
          :value="m.hour"
          class="h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2 text-xs text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          @change="onHourChange($event, idx)"
        >
          <option v-for="h in hours" :key="h" :value="h">{{ String(h).padStart(2, '0') }}시</option>
        </select>
        <!-- 메모 입력 -->
        <input
          :value="m.text"
          type="text"
          placeholder="일정 메모"
          class="min-w-0 flex-1 bg-transparent text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
          @input="onTextInput($event, idx)"
        />
        <!-- 삭제 버튼 -->
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 hover:bg-zinc-800"
          @click="emit('remove', idx)"
        >
          <Trash2 class="h-4 w-4" />
        </button>
      </div>
    </div>
  </section>
</template>
