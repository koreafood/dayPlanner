export type WeatherLocation = {
  name: string
  latitude: number
  longitude: number
  timezone?: string
}

export type DailyWeather = {
  date: string
  weatherCode?: number
  tempMax?: number
  tempMin?: number
  precipitationProbabilityMax?: number
}

export type WeatherSummary = {
  today?: DailyWeather
  tomorrow?: DailyWeather
  units?: {
    temp?: string
    precip?: string
  }
}

const STORAGE_KEY = 'dp_location'

export function getDefaultLocation(): WeatherLocation {
  return {
    name: 'Seoul',
    latitude: 37.5665,
    longitude: 126.978,
    timezone: 'Asia/Seoul',
  }
}

export function readLocation(): WeatherLocation {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return getDefaultLocation()
    const parsed = JSON.parse(raw) as Partial<WeatherLocation>
    if (typeof parsed.latitude !== 'number' || typeof parsed.longitude !== 'number') return getDefaultLocation()
    return {
      name: typeof parsed.name === 'string' && parsed.name.trim() ? parsed.name : 'Custom',
      latitude: parsed.latitude,
      longitude: parsed.longitude,
      timezone: typeof parsed.timezone === 'string' ? parsed.timezone : undefined,
    }
  } catch {
    return getDefaultLocation()
  }
}

export function writeLocation(loc: WeatherLocation) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(loc))
  window.dispatchEvent(new Event('dp_location_changed'))
}

export async function searchLocations(query: string): Promise<WeatherLocation[]> {
  const q = query.trim()
  if (!q) return []
  const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(q)}&count=8&language=ko&format=json`
  const r = await fetch(url)
  if (!r.ok) throw new Error('지역 검색 실패')
  const data = (await r.json()) as {
    results?: Array<{
      name: string
      latitude: number
      longitude: number
      timezone?: string
      country?: string
      admin1?: string
    }>
  }

  return (data.results ?? [])
    .filter((x) => typeof x.latitude === 'number' && typeof x.longitude === 'number')
    .map((x) => {
      const parts = [x.name, x.admin1, x.country].filter(Boolean)
      return {
        name: parts.join(', '),
        latitude: x.latitude,
        longitude: x.longitude,
        timezone: x.timezone,
      }
    })
}

export async function reverseGeocode(latitude: number, longitude: number): Promise<WeatherLocation | null> {
  const url = `https://geocoding-api.open-meteo.com/v1/reverse?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}&language=ko&format=json`
  const r = await fetch(url)
  if (!r.ok) return null
  const data = (await r.json()) as {
    results?: Array<{
      name: string
      latitude: number
      longitude: number
      timezone?: string
      country?: string
      admin1?: string
    }>
  }
  const first = data.results?.[0]
  if (!first) return null
  const parts = [first.name, first.admin1, first.country].filter(Boolean)
  return {
    name: parts.join(', '),
    latitude: first.latitude,
    longitude: first.longitude,
    timezone: first.timezone,
  }
}

export function weatherCodeToText(code?: number): string {
  if (code === undefined || code === null || Number.isNaN(code)) return ''
  if (code === 0) return '맑음'
  if (code === 1) return '대체로 맑음'
  if (code === 2) return '부분적으로 흐림'
  if (code === 3) return '흐림'
  if (code === 45 || code === 48) return '안개'
  if (code === 51 || code === 53 || code === 55) return '이슬비'
  if (code === 56 || code === 57) return '우박성 이슬비'
  if (code === 61 || code === 63 || code === 65) return '비'
  if (code === 66 || code === 67) return '우박성 비'
  if (code === 71 || code === 73 || code === 75) return '눈'
  if (code === 77) return '싸락눈'
  if (code === 80 || code === 81 || code === 82) return '소나기'
  if (code === 85 || code === 86) return '눈 소나기'
  if (code === 95) return '뇌우'
  if (code === 96 || code === 99) return '우박 동반 뇌우'
  return `코드 ${code}`
}

function toDaily(data: {
  time?: string[]
  weathercode?: number[]
  temperature_2m_max?: number[]
  temperature_2m_min?: number[]
  precipitation_probability_max?: number[]
}): DailyWeather[] {
  const times = data.time ?? []
  return times.map((date, idx) => ({
    date,
    weatherCode: data.weathercode?.[idx],
    tempMax: data.temperature_2m_max?.[idx],
    tempMin: data.temperature_2m_min?.[idx],
    precipitationProbabilityMax: data.precipitation_probability_max?.[idx],
  }))
}

export async function fetchTodayTomorrow(loc: WeatherLocation): Promise<WeatherSummary> {
  const daily = 'weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
  const timezone = loc.timezone ? loc.timezone : 'auto'
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${encodeURIComponent(loc.latitude)}&longitude=${encodeURIComponent(loc.longitude)}&daily=${encodeURIComponent(daily)}&timezone=${encodeURIComponent(timezone)}&forecast_days=2`
  const r = await fetch(url)
  if (!r.ok) throw new Error('날씨 불러오기 실패')
  const data = (await r.json()) as {
    daily?: {
      time?: string[]
      weathercode?: number[]
      temperature_2m_max?: number[]
      temperature_2m_min?: number[]
      precipitation_probability_max?: number[]
    }
    daily_units?: {
      temperature_2m_max?: string
      precipitation_probability_max?: string
    }
  }

  const list = toDaily(data.daily ?? {})
  return {
    today: list[0],
    tomorrow: list[1],
    units: {
      temp: data.daily_units?.temperature_2m_max,
      precip: data.daily_units?.precipitation_probability_max,
    },
  }
}

export async function fetchDailyForDate(loc: WeatherLocation, date: string): Promise<DailyWeather | null> {
  const daily = 'weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
  const timezone = loc.timezone ? loc.timezone : 'auto'
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${encodeURIComponent(loc.latitude)}&longitude=${encodeURIComponent(loc.longitude)}&daily=${encodeURIComponent(daily)}&timezone=${encodeURIComponent(timezone)}&start_date=${encodeURIComponent(date)}&end_date=${encodeURIComponent(date)}`
  const r = await fetch(url)
  if (!r.ok) return null
  const data = (await r.json()) as {
    daily?: {
      time?: string[]
      weathercode?: number[]
      temperature_2m_max?: number[]
      temperature_2m_min?: number[]
      precipitation_probability_max?: number[]
    }
  }
  const list = toDaily(data.daily ?? {})
  return list[0] ?? null
}

