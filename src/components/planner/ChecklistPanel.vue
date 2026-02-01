<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import type { ChecklistItem } from '@/composables/usePlanner'
import { computed } from 'vue'

const items = defineModel<ChecklistItem[]>('items', { required: true })
const emit = defineEmits<{ (e: 'add'): void; (e: 'remove', id: string): void }>()

function sortByOrder(list: ChecklistItem[]) {
  return list.slice().sort((a, b) => a.order - b.order)
}

const sorted = computed(() => sortByOrder(items.value ?? []))
</script>

<template>
  <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
    <div class="mb-3 flex items-center justify-between">
      <div class="text-sm font-semibold text-zinc-100">체크리스트</div>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
        @click="emit('add')"
      >
        <Plus class="h-4 w-4" />
        추가
      </button>
    </div>

    <div class="space-y-2">
      <div
        v-for="it in sorted"
        :key="it.id"
        class="rounded-xl border border-zinc-800 bg-zinc-900 p-3"
      >
        <div class="flex items-start gap-3">
          <input v-model="it.checked" type="checkbox" class="mt-1 h-4 w-4 accent-indigo-500" />
          <div class="min-w-0 flex-1">
            <input
              v-model="it.text"
              type="text"
              placeholder="할 일"
              class="w-full bg-transparent text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
            />
            <input
              v-model="it.note"
              type="text"
              placeholder="항목별 메모(1줄)"
              class="mt-1 w-full bg-transparent text-xs text-zinc-300 placeholder:text-zinc-600 focus:outline-none"
            />
          </div>
          <button
            type="button"
            class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 hover:bg-zinc-800"
            @click="emit('remove', it.id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </div>

      <div v-if="sorted.length === 0" class="rounded-xl border border-dashed border-zinc-800 p-6 text-center">
        <div class="text-xs text-zinc-400">체크리스트가 비어있습니다.</div>
      </div>
    </div>
  </section>
</template>
