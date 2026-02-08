<script setup lang="ts">
/*
  GridBoard
  - 목적: 격자 보드 위에 텍스트/이미지 블록을 배치하고 드래그로 위치 이동, 업데이트/삭제/업로드 이벤트 제공
  - v-model:
    * grid: GridPayload (blocks 배열과 보드 상태)
  - 이벤트:
    * addText: 텍스트 블록 추가 요청
    * remove(id): 특정 블록 삭제
    * update(block): 블록 내용/좌표 갱신
    * upload(file): 이미지 업로드 요청
  - 드래그 로직:
    * header 영역 pointerdown → drag 상태 저장 → root에서 pointermove로 좌표 업데이트 → pointerup으로 종료
*/
import { ref } from 'vue'
import { ImageUp, Plus, Trash2 } from 'lucide-vue-next'
import type { GridBlock, GridPayload } from '@/composables/usePlanner'

const grid = defineModel<GridPayload>('grid', { required: true })
const emit = defineEmits<{
  (e: 'addText'): void
  (e: 'remove', id: string): void
  (e: 'update', block: GridBlock): void
  (e: 'upload', file: File): void
}>()

const rootRef = ref<HTMLDivElement | null>(null)
const drag = ref<
  | {
      id: string
      startX: number
      startY: number
      originX: number
      originY: number
    }
  | undefined
>(undefined)

function onPointerMove(e: PointerEvent) {
  if (!drag.value) return
  const b = grid.value.blocks.find((x) => x.id === drag.value?.id)
  if (!b) return
  const dx = e.clientX - drag.value.startX
  const dy = e.clientY - drag.value.startY
  const next = { ...b, x: Math.max(0, drag.value.originX + dx), y: Math.max(0, drag.value.originY + dy) }
  emit('update', next)
}

function onPointerUp() {
  drag.value = undefined
}

function onHeaderPointerDown(e: Event, b: GridBlock) {
  const pe = e as PointerEvent
  if (!rootRef.value) return
  drag.value = {
    id: b.id,
    startX: pe.clientX,
    startY: pe.clientY,
    originX: b.x,
    originY: b.y,
  }
  rootRef.value.setPointerCapture(pe.pointerId)
  pe.preventDefault()
}

function onRootPointerMove(e: Event) {
  onPointerMove(e as PointerEvent)
}

function onRootPointerUp() {
  onPointerUp()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (!f) return
  emit('upload', f)
}

function setText(b: GridBlock, text: string) {
  emit('update', { ...b, text })
}

function onTextInput(e: Event, b: GridBlock) {
  const target = e.target as HTMLTextAreaElement | null
  setText(b, target?.value ?? '')
}
</script>

<template>
  <!-- 모눈 보드 패널 -->
  <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
    <div class="mb-3 flex items-center justify-between">
      <div class="text-sm font-semibold text-zinc-100">모눈</div>
      <div class="flex items-center gap-2">
        <!-- 텍스트 블록 추가 -->
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
          @click="emit('addText')"
        >
          <Plus class="h-4 w-4" />
          텍스트
        </button>
        <!-- 이미지 업로드 -->
        <label
          class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
        >
          <ImageUp class="h-4 w-4" />
          이미지
          <input type="file" accept="image/*" class="hidden" @change="onFileChange" />
        </label>
      </div>
    </div>

    <!-- 보드 영역: 포인터 이벤트 처리 -->
    <div
      ref="rootRef"
      class="relative h-[420px] overflow-hidden rounded-xl border border-zinc-800 bg-[linear-gradient(to_right,rgba(39,55,90,0.6)_1px,transparent_1px),linear-gradient(to_bottom,rgba(39,55,90,0.6)_1px,transparent_1px)] bg-[size:24px_24px]"
      @pointermove="onRootPointerMove"
      @pointerup="onRootPointerUp"
      @pointercancel="onRootPointerUp"
      @pointerleave="onRootPointerUp"
    >
      <!-- 블록 렌더링 -->
      <div
        v-for="b in grid.blocks"
        :key="b.id"
        class="absolute rounded-xl border border-zinc-800 bg-zinc-950/90 shadow-sm"
        :style="{ left: b.x + 'px', top: b.y + 'px', width: b.w + 'px', height: b.h + 'px' }"
      >
        <!-- 블록 헤더: 타입 표시, 삭제 -->
        <div
          class="flex items-center justify-between gap-2 border-b border-zinc-800 px-2 py-1"
          @pointerdown="onHeaderPointerDown($event, b)"
        >
          <div class="text-[11px] font-semibold text-zinc-400">{{ b.type === 'text' ? '텍스트' : '이미지' }}</div>
          <button
            type="button"
            class="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-200 hover:bg-zinc-800"
            @click.stop="emit('remove', b.id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>

        <!-- 블록 내용 -->
        <div class="h-[calc(100%-34px)] p-2">
          <textarea
            v-if="b.type === 'text'"
            :value="b.text || ''"
            placeholder="메모"
            class="h-full w-full resize-none rounded-lg border border-zinc-800 bg-zinc-900 px-2 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
            @input="onTextInput($event, b)"
          />
          <div v-else class="h-full w-full overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900">
            <img
              v-if="b.image"
              :src="b.image.url"
              class="h-full w-full object-contain"
              alt="uploaded"
              draggable="false"
            />
            <div v-else class="flex h-full items-center justify-center text-xs text-zinc-500">이미지 없음</div>
          </div>
        </div>
      </div>

      <!-- 빈 상태 안내 -->
      <div
        v-if="grid.blocks.length === 0"
        class="absolute inset-0 flex items-center justify-center text-center"
      >
        <div class="rounded-xl border border-dashed border-zinc-800 bg-zinc-950/60 px-5 py-4">
          <div class="text-xs text-zinc-300">모눈 메모가 비어있습니다.</div>
          <div class="mt-1 text-[11px] text-zinc-500">상단 버튼으로 텍스트/이미지를 추가하세요.</div>
        </div>
      </div>
    </div>
  </section>
</template>
