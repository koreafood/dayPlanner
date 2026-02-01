import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { WeatherLocation, WeatherSummary } from '@/lib/weather'
import { fetchTodayTomorrow, readLocation } from '@/lib/weather'

export function useWeather() {
  const location = ref<WeatherLocation>(readLocation())
  const summary = ref<WeatherSummary | null>(null)
  const loading = ref(false)
  const error = ref<string>('')

  async function refresh() {
    loading.value = true
    error.value = ''
    try {
      location.value = readLocation()
      summary.value = await fetchTodayTomorrow(location.value)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '날씨 불러오기 실패'
      summary.value = null
    } finally {
      loading.value = false
    }
  }

  function onLocationChanged() {
    refresh()
  }

  onMounted(() => {
    window.addEventListener('dp_location_changed', onLocationChanged)
    refresh()
  })

  onBeforeUnmount(() => {
    window.removeEventListener('dp_location_changed', onLocationChanged)
  })

  return { location, summary, loading, error, refresh }
}

