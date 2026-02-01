<script setup lang="ts">
defineProps<{ title: string; date: string }>()
</script>

<template>
  <header class="w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
      <div class="text-sm font-semibold tracking-tight text-zinc-100">{{ title }}</div>
      <div
        class="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-200"
      >
        {{ date }}
      </div>
    </div>
  </header>
</template>

