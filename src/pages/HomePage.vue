<script setup lang="ts">
import PlannerHeader from '@/components/planner/PlannerHeader.vue'
import MonthCalendar from '@/components/planner/MonthCalendar.vue'
import ChecklistPanel from '@/components/planner/ChecklistPanel.vue'
import LineMemosPanel from '@/components/planner/LineMemosPanel.vue'
import MemoBoardPanel from '@/components/planner/MemoBoardPanel.vue'
import GridBoard from '@/components/planner/GridBoard.vue'
import { usePlanner } from '@/composables/usePlanner'
import { Download, Printer, Save } from 'lucide-vue-next'

const {
  selectedDate,
  day,
  status,
  statusLabel,
  errorMessage,
  dirty,
  load,
  save,
  selectDate,
  addChecklistItem,
  removeChecklistItem,
  addScheduleMemo,
  removeScheduleMemo,
  addTextBlock,
  removeBlock,
  updateBlock,
  uploadAndAddImage,
} = usePlanner()

function onSelectDate(date: string) {
  selectDate(date)
}

function onReload() {
  load(selectedDate.value)
}

async function onSave() {
  await save()
}

async function onPrint() {
  if (dirty.value) {
    const ok = await save()
    if (!ok) return
  }
  const url = `/print.html?date=${encodeURIComponent(selectedDate.value)}&autoprint=1`
  window.open(url, '_blank', 'noopener,noreferrer')
}

function onUpload(file: File) {
  uploadAndAddImage(file)
}
</script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-100">
    <PlannerHeader title="Day Planner" :date="selectedDate" />

    <main class="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-[320px,1fr]">
      <aside class="space-y-4">
        <MonthCalendar :selected-date="selectedDate" :selected-day-note="day.dayNote" @select="onSelectDate" />

        <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
          <div class="text-xs font-semibold text-zinc-200">한줄메모</div>
          <input
            v-model="day.dayNote"
            type="text"
            maxlength="80"
            placeholder="달력에 표시될 한 줄 메모"
            class="mt-2 h-10 w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          />
          <div class="mt-2 text-[11px] text-zinc-500">달력은 파란 점으로 표시되고, 마우스 오버 시 툴팁으로 보입니다.</div>
        </section>

        <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-xs font-semibold text-zinc-200">상태</div>
              <div class="mt-1 text-sm font-semibold" :class="status === 'error' ? 'text-rose-300' : 'text-zinc-100'">
                {{ statusLabel }}
              </div>
            </div>
            <div class="text-right">
              <div class="text-[11px] text-zinc-500">updatedAt</div>
              <div class="mt-1 text-xs text-zinc-300">{{ day.updatedAt }}</div>
            </div>
          </div>
          <div v-if="errorMessage" class="mt-2 text-xs text-rose-300">{{ errorMessage }}</div>
          <div class="mt-3 flex items-center gap-2">
            <button
              type="button"
              class="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-zinc-900 px-3 py-2 text-sm font-semibold text-zinc-100 ring-1 ring-zinc-800 hover:bg-zinc-800"
              @click="onReload"
            >
              <Download class="h-4 w-4" />
              불러오기
            </button>
            <button
              type="button"
              class="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-zinc-900 px-3 py-2 text-sm font-semibold text-zinc-100 ring-1 ring-zinc-800 hover:bg-zinc-800"
              @click="onPrint"
            >
              <Printer class="h-4 w-4" />
              프린트
            </button>
            <button
              type="button"
              class="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
              @click="onSave"
            >
              <Save class="h-4 w-4" />
              저장
            </button>
          </div>
        </section>
      </aside>

      <section class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="space-y-4">
          <ChecklistPanel
            v-model:items="day.checklist"
            @add="addChecklistItem"
            @remove="removeChecklistItem"
          />
          <LineMemosPanel
            v-model:schedule-memos="day.scheduleMemos"
            @add="addScheduleMemo"
            @remove="removeScheduleMemo"
          />
        </div>

        <div class="space-y-4">
          <MemoBoardPanel v-model:board-memo="day.boardMemo" />
          <GridBoard
            v-model:grid="day.grid"
            @add-text="addTextBlock"
            @remove="removeBlock"
            @update="updateBlock"
            @upload="onUpload"
          />
        </div>
      </section>
    </main>
  </div>
</template>
