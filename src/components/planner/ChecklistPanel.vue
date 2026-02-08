<script setup lang="ts">
/* 
  ChecklistPanel
  - 목적: 체크리스트 항목을 생성/표시/삭제하고 각 항목의 상태(체크 여부, 텍스트, 메모)를 편집
  - 입력(v-model): items (ChecklistItem[]), 상위 컴포넌트에서 양방향 바인딩
  - 이벤트(emit):
    * add: 새로운 체크리스트 항목을 추가하라는 신호를 상위로 전달
    * remove(id): 특정 항목을 삭제하라는 신호를 상위로 전달
  - 렌더링:
    * 항목은 order 값으로 정렬되어 표시됨
    * 각 항목은 체크박스, 텍스트 입력, 메모 입력, 삭제 버튼을 포함
  - 의존성:
    * lucide-vue-next: 아이콘 컴포넌트(Plus, Trash2)
    * vue: computed, defineModel, defineEmits 등
*/
import { Plus, Trash2 } from 'lucide-vue-next'
import type { ChecklistItem } from '@/composables/usePlanner'
import { computed } from 'vue'

// 상위와 양방향 바인딩되는 체크리스트 항목 배열
const items = defineModel<ChecklistItem[]>('items', { required: true })
// 상위 컴포넌트로 전달할 이벤트 정의
const emit = defineEmits<{ (e: 'add'): void; (e: 'remove', id: string): void }>()

// 표시 순서를 위해 order 기준으로 정렬하는 순수 함수
function sortByOrder(list: ChecklistItem[]) {
  return list.slice().sort((a, b) => a.order - b.order)
}

// 반응형 정렬된 목록
const sorted = computed(() => sortByOrder(items.value ?? []))
</script>

<template>
  <!-- 컴포넌트 컨테이너: 라운딩/테두리/배경/패딩 -->
  <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
    <!-- 헤더: 제목과 항목 추가 버튼 -->
    <div class="mb-3 flex items-center justify-between">
      <div class="text-sm font-semibold text-zinc-100">체크리스트</div>
      <!-- 항목 추가 버튼: 상위로 'add' 이벤트 emit -->
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
        @click="emit('add')"
      >
        <Plus class="h-4 w-4" />
        추가
      </button>
    </div>

    <!-- 항목 리스트 컨테이너: 항목 간 간격 -->
    <div class="space-y-2">
      <!-- 정렬된 항목을 반복 렌더링 -->
      <div
        v-for="it in sorted"
        :key="it.id"
        class="rounded-xl border border-zinc-800 bg-zinc-900 p-3"
      >
        <div class="flex items-start gap-3">
          <!-- 체크 여부 토글 -->
          <input v-model="it.checked" type="checkbox" class="mt-1 h-4 w-4 accent-indigo-500" />
          <div class="min-w-0 flex-1">
            <!-- 항목 텍스트 입력 -->
            <input
              v-model="it.text"
              type="text"
              placeholder="할 일"
              class="w-full bg-transparent text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
            />
            <!-- 항목 메모 입력(한 줄) -->
            <input
              v-model="it.note"
              type="text"
              placeholder="항목별 메모(1줄)"
              class="mt-1 w-full bg-transparent text-xs text-zinc-300 placeholder:text-zinc-600 focus:outline-none"
            />
          </div>
          <!-- 항목 삭제 버튼: 상위로 'remove' 이벤트 emit -->
          <button
            type="button"
            class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 hover:bg-zinc-800"
            @click="emit('remove', it.id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </div>

      <!-- 빈 상태 표시 -->
      <div v-if="sorted.length === 0" class="rounded-xl border border-dashed border-zinc-800 p-6 text-center">
        <div class="text-xs text-zinc-400">체크리스트가 비어있습니다.</div>
      </div>
    </div>
  </section>
</template>
