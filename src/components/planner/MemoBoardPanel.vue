<script setup lang="ts">
const boardMemo = defineModel<string>('boardMemo', { required: true })
</script>

<template>
  <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
    <div class="mb-3 flex items-center justify-between">
      <div class="text-sm font-semibold text-zinc-100">메모판</div>
      <div class="text-[11px] text-zinc-400">자유 메모</div>
    </div>

    <textarea
      v-model="boardMemo"
      rows="10"
      placeholder="메모를 작성하세요"
      class="min-h-[240px] w-full resize-none rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
    />
  </section>
</template>

