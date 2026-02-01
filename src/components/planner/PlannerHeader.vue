<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Settings } from 'lucide-vue-next'

defineProps<{ title: string; date: string }>()
</script>

<template>
  <header class="w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
      <div class="text-sm font-semibold tracking-tight text-zinc-100">{{ title }}</div>
      <div class="flex items-center gap-2">
        <RouterLink
          to="/setup"
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-200 hover:bg-zinc-800"
          title="설정"
        >
          <Settings class="h-4 w-4" />
        </RouterLink>
        <div
          class="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-200"
        >
          {{ date }}
        </div>
      </div>
    </div>
  </header>
</template>
