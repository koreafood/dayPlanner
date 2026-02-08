<script setup lang="ts">
/*
  PlannerHeader
  - 목적: 상단 헤더 영역에서 제목과 현재 날짜, 설정 페이지로 이동 버튼을 표시
  - props:
    * title: 헤더 타이틀 텍스트
    * date: 선택된 날짜 문자열
  - 의존성:
    * vue-router: RouterLink로 설정 페이지로 이동
    * lucide-vue-next: Settings 아이콘
*/
import { RouterLink } from 'vue-router'
import { Settings } from 'lucide-vue-next'

defineProps<{ title: string; date: string }>()
</script>

<template>
  <!-- 헤더 컨테이너: 블러 배경과 하단 보더 -->
  <header class="w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
      <!-- 제목 표시 -->
      <div class="text-sm font-semibold tracking-tight text-zinc-100">{{ title }}</div>
      <div class="flex items-center gap-2">
        <!-- 설정 페이지 이동 버튼 -->
        <RouterLink
          to="/setup"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-200 hover:bg-zinc-800"
          title="설정"
        >
          <Settings class="h-4 w-4" />
        </RouterLink>
        <!-- 현재 날짜 표시 -->
        <div
          class="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-200"
        >
          {{ date }}
        </div>
      </div>
    </div>
  </header>
</template>
