import { computed, ref, watch } from 'vue'

export type ISODate = string

export type ChecklistItem = {
  id: string
  text: string
  checked: boolean
  order: number
  note: string
}

export type ScheduleMemo = {
  hour: number
  text: string
}

export type GridImage = {
  id: string
  url: string
  width: number
  height: number
}

export type GridBlock = {
  id: string
  x: number
  y: number
  w: number
  h: number
  type: 'text' | 'image'
  text?: string
  image?: GridImage
}

export type GridPayload = {
  cols: number
  rows: number
  blocks: GridBlock[]
}

export type DayPayload = {
  date: ISODate
  checklist: ChecklistItem[]
  dayNote: string
  scheduleMemos: ScheduleMemo[]
  boardMemo: string
  grid: GridPayload
  updatedAt: string
}

type Status = 'idle' | 'loading' | 'saving' | 'error'

function toISODate(d: Date): ISODate {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function defaultDay(date: ISODate): DayPayload {
  return {
    date,
    checklist: [],
    dayNote: '',
    scheduleMemos: [],
    boardMemo: '',
    grid: { cols: 24, rows: 24, blocks: [] },
    updatedAt: new Date().toISOString(),
  }
}

async function apiGetDay(date: ISODate): Promise<DayPayload> {
  const r = await fetch(`/api/days/${encodeURIComponent(date)}`)
  if (!r.ok) throw new Error('불러오기 실패')
  return (await r.json()) as DayPayload
}

async function apiPutDay(payload: DayPayload): Promise<{ ok: boolean; updatedAt: string }> {
  const r = await fetch(`/api/days/${encodeURIComponent(payload.date)}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error('저장 실패')
  return (await r.json()) as { ok: boolean; updatedAt: string }
}

async function apiUploadImage(date: ISODate, file: File): Promise<GridImage> {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch(`/api/uploads/images?date=${encodeURIComponent(date)}`, {
    method: 'POST',
    body: fd,
  })
  if (!r.ok) throw new Error('이미지 업로드 실패')
  return (await r.json()) as GridImage
}

export function usePlanner() {
  const selectedDate = ref<ISODate>(toISODate(new Date()))
  const day = ref<DayPayload>(defaultDay(selectedDate.value))
  const status = ref<Status>('idle')
  const errorMessage = ref<string>('')
  const dirty = ref(false)
  const hydrating = ref(false)
  const switchingDate = ref(false)

  const statusLabel = computed(() => {
    if (status.value === 'loading') return '불러오는 중'
    if (status.value === 'saving') return '저장 중'
    if (status.value === 'error') return '오류'
    if (dirty.value) return '저장 필요'
    return '저장됨'
  })

  watch(
    day,
    () => {
      if (hydrating.value) return
      dirty.value = true
    },
    { deep: true }
  )

  async function load(date: ISODate) {
    status.value = 'loading'
    errorMessage.value = ''
    try {
      const data = await apiGetDay(date)
      hydrating.value = true
      day.value = data
      selectedDate.value = date
      dirty.value = false
      status.value = 'idle'
    } catch (e) {
      status.value = 'error'
      errorMessage.value = e instanceof Error ? e.message : '불러오기 실패'
    } finally {
      hydrating.value = false
    }
  }

  async function save() {
    status.value = 'saving'
    errorMessage.value = ''
    try {
      const res = await apiPutDay(day.value)
      hydrating.value = true
      day.value = { ...day.value, updatedAt: res.updatedAt }
      dirty.value = false
      status.value = 'idle'
      return true
    } catch (e) {
      status.value = 'error'
      errorMessage.value = e instanceof Error ? e.message : '저장 실패'
      return false
    } finally {
      hydrating.value = false
    }
  }

  async function selectDate(next: ISODate) {
    if (next === selectedDate.value) return
    if (switchingDate.value) return
    switchingDate.value = true
    try {
      if (dirty.value) {
        const ok = await save()
        if (!ok) return
      }
      await load(next)
    } finally {
      switchingDate.value = false
    }
  }

  function addChecklistItem() {
    const id = crypto.randomUUID()
    const order = day.value.checklist.length
    day.value.checklist.push({ id, text: '', checked: false, order, note: '' })
  }

  function removeChecklistItem(id: string) {
    day.value.checklist = day.value.checklist.filter((i) => i.id !== id)
    day.value.checklist = day.value.checklist
      .slice()
      .sort((a, b) => a.order - b.order)
      .map((i, idx) => ({ ...i, order: idx }))
  }

  function addScheduleMemo() {
    day.value.scheduleMemos.push({ hour: new Date().getHours(), text: '' })
  }

  function removeScheduleMemo(index: number) {
    day.value.scheduleMemos = day.value.scheduleMemos.filter((_, i) => i !== index)
  }

  function addTextBlock() {
    const id = crypto.randomUUID()
    day.value.grid.blocks.push({ id, type: 'text', x: 20, y: 20, w: 240, h: 140, text: '' })
  }

  function removeBlock(id: string) {
    day.value.grid.blocks = day.value.grid.blocks.filter((b) => b.id !== id)
  }

  function updateBlock(next: GridBlock) {
    const idx = day.value.grid.blocks.findIndex((b) => b.id === next.id)
    if (idx < 0) return
    const blocks = day.value.grid.blocks.slice()
    blocks[idx] = next
    day.value.grid.blocks = blocks
  }

  async function uploadAndAddImage(file: File) {
    const img = await apiUploadImage(selectedDate.value, file)
    const id = crypto.randomUUID()
    const w = Math.min(320, Math.max(160, img.width || 240))
    const h = Math.min(260, Math.max(120, img.height || 180))
    day.value.grid.blocks.push({ id, type: 'image', x: 24, y: 24, w, h, image: img })
  }

  load(selectedDate.value)

  return {
    selectedDate,
    day,
    status,
    statusLabel,
    errorMessage,
    dirty,
    load,
    save,
    selectDate,
    addChecklistItem,
    removeChecklistItem,
    addScheduleMemo,
    removeScheduleMemo,
    addTextBlock,
    removeBlock,
    updateBlock,
    uploadAndAddImage,
  }
}
