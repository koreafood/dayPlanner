<script setup lang="ts">
import { computed } from 'vue'
import { useWeather } from '@/composables/useWeather'
import { weatherCodeToText } from '@/lib/weather'

const { location, summary, loading, error, refresh } = useWeather()

const todayText = computed(() => {
  const d = summary.value?.today
  if (!d) return ''
  const wx = weatherCodeToText(d.weatherCode)
  const tmin = d.tempMin !== undefined ? Math.round(d.tempMin) : undefined
  const tmax = d.tempMax !== undefined ? Math.round(d.tempMax) : undefined
  const pop = d.precipitationProbabilityMax
  const temp = tmin !== undefined && tmax !== undefined ? `${tmin}~${tmax}°` : ''
  const precip = pop !== undefined ? `강수 ${Math.round(pop)}%` : ''
  return [wx, temp, precip].filter(Boolean).join(' · ')
})

const tomorrowText = computed(() => {
  const d = summary.value?.tomorrow
  if (!d) return ''
  const wx = weatherCodeToText(d.weatherCode)
  const tmin = d.tempMin !== undefined ? Math.round(d.tempMin) : undefined
  const tmax = d.tempMax !== undefined ? Math.round(d.tempMax) : undefined
  const pop = d.precipitationProbabilityMax
  const temp = tmin !== undefined && tmax !== undefined ? `${tmin}~${tmax}°` : ''
  const precip = pop !== undefined ? `강수 ${Math.round(pop)}%` : ''
  return [wx, temp, precip].filter(Boolean).join(' · ')
})
</script>

<template>
  <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
    <div class="flex items-center justify-between">
      <div>
        <div class="text-xs font-semibold text-zinc-200">날씨</div>
        <div class="mt-1 text-[11px] text-zinc-500">{{ location.name }}</div>
      </div>
      <button
        type="button"
        class="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
        @click="refresh"
      >
        새로고침
      </button>
    </div>

    <div v-if="error" class="mt-2 text-xs text-rose-300">{{ error }}</div>

    <div class="mt-3 space-y-1">
      <div class="flex items-center justify-between gap-3 text-sm">
        <div class="text-zinc-300">오늘</div>
        <div class="min-w-0 flex-1 text-right text-zinc-100">
          <span v-if="loading" class="text-zinc-500">불러오는 중…</span>
          <span v-else>{{ todayText || '-' }}</span>
        </div>
      </div>
      <div class="flex items-center justify-between gap-3 text-sm">
        <div class="text-zinc-300">내일</div>
        <div class="min-w-0 flex-1 text-right text-zinc-100">
          <span v-if="loading" class="text-zinc-500">불러오는 중…</span>
          <span v-else>{{ tomorrowText || '-' }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

