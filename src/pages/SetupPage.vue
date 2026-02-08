<script setup lang="ts">
/*
  SetupPage
  - 목적: 날씨 지역 설정 페이지로 현재 저장된 지역 확인, 내 위치 사용, 텍스트 검색을 통해 지역 선택
  - 의존성:
    * vue-router: 설정 완료 후 홈으로 이동
    * lib/weather: 위치 저장/읽기, 역지오코딩, 검색
  - 주요 상태:
    * current: 선택된 지역
    * query/results: 검색어와 결과 목록
    * loading/error: 진행 상태 및 오류 메시지
*/
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { WeatherLocation } from '@/lib/weather'
import { readLocation, reverseGeocode, searchLocations, writeLocation } from '@/lib/weather'

const router = useRouter()

const current = ref<WeatherLocation>(readLocation())
const query = ref('')
const results = ref<WeatherLocation[]>([])
const loading = ref(false)
const error = ref('')

const canSearch = computed(() => query.value.trim().length >= 2)

async function onSearch() {
  if (!canSearch.value) return
  loading.value = true
  error.value = ''
  try {
    results.value = await searchLocations(query.value)
    if (results.value.length === 0) error.value = '검색 결과가 없습니다.'
  } catch (e) {
    error.value = e instanceof Error ? e.message : '검색 실패'
    results.value = []
  } finally {
    loading.value = false
  }
}

function onSelect(loc: WeatherLocation) {
  current.value = loc
  writeLocation(loc)
}

async function onUseMyLocation() {
  if (!navigator.geolocation) {
    error.value = '이 브라우저는 위치 기능을 지원하지 않습니다.'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: false, timeout: 8000 })
    })
    const loc = await reverseGeocode(pos.coords.latitude, pos.coords.longitude)
    if (!loc) {
      const fallback: WeatherLocation = {
        name: '내 위치',
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        timezone: undefined,
      }
      current.value = fallback
      writeLocation(fallback)
      return
    }
    current.value = loc
    writeLocation(loc)
  } catch {
    error.value = '현재 위치를 가져오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

function goHome() {
  router.push('/')
}
</script>

<template>
  <!-- 페이지 컨테이너 -->
  <div class="min-h-screen bg-zinc-950 text-zinc-100">
    <!-- 헤더: 설정 타이틀과 돌아가기 -->
    <header class="w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
      <div class="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
        <div class="text-sm font-semibold tracking-tight text-zinc-100">설정</div>
        <button
          type="button"
          class="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
          @click="goHome"
        >
          돌아가기
        </button>
      </div>
    </header>

    <!-- 본문: 현재 지역과 지역 검색 -->
    <main class="mx-auto max-w-3xl space-y-4 px-4 py-4">
      <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
        <div class="text-xs font-semibold text-zinc-200">현재 지역</div>
        <div class="mt-2 rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2">
          <div class="text-sm font-semibold text-zinc-100">{{ current.name }}</div>
          <div class="mt-1 text-[11px] text-zinc-500">
            {{ current.latitude.toFixed(4) }}, {{ current.longitude.toFixed(4) }}
            <span v-if="current.timezone"> · {{ current.timezone }}</span>
          </div>
        </div>
        <div class="mt-3">
          <button
            type="button"
            class="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
            :disabled="loading"
            @click="onUseMyLocation"
          >
            내 위치 사용
          </button>
        </div>
      </section>

      <section class="rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
        <div class="text-xs font-semibold text-zinc-200">지역 검색</div>
        <div class="mt-2 flex gap-2">
          <input
            v-model="query"
            type="text"
            placeholder="예: 서울, 부산, 제주"
            class="h-10 flex-1 rounded-xl border border-zinc-800 bg-zinc-900 px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
            @keydown.enter="onSearch"
          />
          <button
            type="button"
            class="rounded-xl bg-indigo-600 px-4 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            :disabled="loading || !canSearch"
            @click="onSearch"
          >
            검색
          </button>
        </div>

        <div v-if="error" class="mt-2 text-xs text-rose-300">{{ error }}</div>
        <div v-if="loading" class="mt-2 text-xs text-zinc-500">불러오는 중…</div>

        <div v-if="results.length" class="mt-3 space-y-2">
          <button
            v-for="r in results"
            :key="r.name + String(r.latitude) + String(r.longitude)"
            type="button"
            class="w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-left hover:bg-zinc-800"
            @click="onSelect(r)"
          >
            <div class="text-sm font-semibold text-zinc-100">{{ r.name }}</div>
            <div class="mt-1 text-[11px] text-zinc-500">
              {{ r.latitude.toFixed(4) }}, {{ r.longitude.toFixed(4) }}
              <span v-if="r.timezone"> · {{ r.timezone }}</span>
            </div>
          </button>
        </div>

        <div class="mt-3 text-[11px] text-zinc-500">
          날씨 API: Open-Meteo(Geocoding + Forecast, API Key 불필요)
        </div>
      </section>
    </main>
  </div>
</template>
