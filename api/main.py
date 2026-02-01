from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_date(date_str: str) -> str:
    try:
        return datetime.fromisoformat(date_str).date().isoformat()
    except Exception:
        raise HTTPException(status_code=400, detail='date는 YYYY-MM-DD 형식이어야 합니다.')


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'app.db'
UPLOAD_DIR = BASE_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_init() -> None:
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS day_entries (
              date TEXT PRIMARY KEY,
              checklist_json TEXT NOT NULL DEFAULT '[]',
              line_memo TEXT NOT NULL DEFAULT '',
              board_memo TEXT NOT NULL DEFAULT '',
              grid_json TEXT NOT NULL DEFAULT '{"cols":24,"rows":24,"blocks":[]}',
              updated_at TEXT NOT NULL
            );
            """
        )

        cols = {row["name"] for row in conn.execute("PRAGMA table_info(day_entries)").fetchall()}
        if "day_note" not in cols:
            conn.execute("ALTER TABLE day_entries ADD COLUMN day_note TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS grid_images (
              id TEXT PRIMARY KEY,
              day_date TEXT NOT NULL,
              filename TEXT NOT NULL,
              width INTEGER NOT NULL,
              height INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_grid_images_day_date
            ON grid_images(day_date);
            """
        )


class ChecklistItem(BaseModel):
    id: str
    text: str
    checked: bool
    order: int
    note: str = ''


class ScheduleMemo(BaseModel):
    hour: int = Field(ge=0, le=23)
    text: str = ''


class GridImage(BaseModel):
    id: str
    url: str
    width: int
    height: int


class GridBlock(BaseModel):
    id: str
    x: float
    y: float
    w: float
    h: float
    type: Literal['text', 'image']
    text: str | None = None
    image: GridImage | None = None


class GridPayload(BaseModel):
    cols: int = 24
    rows: int = 24
    blocks: list[GridBlock] = Field(default_factory=list)


class DayPayload(BaseModel):
    date: str
    checklist: list[ChecklistItem] = Field(default_factory=list)
    dayNote: str = ''
    scheduleMemos: list[ScheduleMemo] = Field(default_factory=list)
    boardMemo: str = ''
    grid: GridPayload = Field(default_factory=GridPayload)
    updatedAt: str


class SaveResult(BaseModel):
    ok: bool
    updatedAt: str


class MonthNotesResult(BaseModel):
    notes: dict[str, str]


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def on_startup() -> None:
    db_init()


app.mount('/uploads', StaticFiles(directory=str(UPLOAD_DIR)), name='uploads')


def day_default(date_str: str) -> DayPayload:
    return DayPayload(
        date=date_str,
        checklist=[],
        dayNote='',
        scheduleMemos=[],
        boardMemo='',
        grid=GridPayload(cols=24, rows=24, blocks=[]),
        updatedAt=utc_now_iso(),
    )


@app.get('/api/days/{date}', response_model=DayPayload)
def get_day(date: str) -> DayPayload:
    date_key = parse_iso_date(date)
    with db_connect() as conn:
        row = conn.execute('SELECT * FROM day_entries WHERE date = ?', (date_key,)).fetchone()

    if row is None:
        return day_default(date_key)

    try:
        checklist = json.loads(row['checklist_json'] or '[]')
    except Exception:
        checklist = []

    schedule_memos: list[dict] = []
    raw_schedule = row['line_memo'] or ''
    if raw_schedule:
        try:
            parsed = json.loads(raw_schedule)
            if isinstance(parsed, list):
                schedule_memos = parsed
        except Exception:
            lines = [x for x in str(raw_schedule).split('\n')]
            schedule_memos = [
                {"hour": min(i, 23), "text": line}
                for i, line in enumerate(lines)
                if line is not None
            ]

    try:
        grid = json.loads(row['grid_json'] or '{"cols":24,"rows":24,"blocks":[]}')
    except Exception:
        grid = {"cols": 24, "rows": 24, "blocks": []}

    return DayPayload(
        date=row['date'],
        checklist=checklist,
        dayNote=row['day_note'] if 'day_note' in row.keys() else '',
        scheduleMemos=schedule_memos,
        boardMemo=row['board_memo'] or '',
        grid=grid,
        updatedAt=row['updated_at'],
    )


@app.put('/api/days/{date}', response_model=SaveResult)
def put_day(date: str, payload: DayPayload) -> SaveResult:
    date_key = parse_iso_date(date)
    body_key = parse_iso_date(payload.date)
    if date_key != body_key:
        raise HTTPException(status_code=400, detail='path date와 body date가 일치해야 합니다.')

    updated_at = utc_now_iso()
    checklist_json = json.dumps([i.model_dump() for i in payload.checklist], ensure_ascii=False)
    schedule_json = json.dumps([i.model_dump() for i in payload.scheduleMemos], ensure_ascii=False)
    grid_json = json.dumps(payload.grid.model_dump(), ensure_ascii=False)

    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO day_entries(date, checklist_json, day_note, line_memo, board_memo, grid_json, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
              checklist_json=excluded.checklist_json,
              day_note=excluded.day_note,
              line_memo=excluded.line_memo,
              board_memo=excluded.board_memo,
              grid_json=excluded.grid_json,
              updated_at=excluded.updated_at
            """,
            (date_key, checklist_json, payload.dayNote, schedule_json, payload.boardMemo, grid_json, updated_at),
        )

    return SaveResult(ok=True, updatedAt=updated_at)


@app.get('/api/month-notes', response_model=MonthNotesResult)
def get_month_notes(year: int, month: int) -> MonthNotesResult:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail='month는 1~12 범위여야 합니다.')
    start = datetime(year, month, 1).date().isoformat()
    if month == 12:
        end = datetime(year + 1, 1, 1).date().isoformat()
    else:
        end = datetime(year, month + 1, 1).date().isoformat()

    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT date, day_note
            FROM day_entries
            WHERE date >= ? AND date < ? AND day_note != ''
            """,
            (start, end),
        ).fetchall()

    notes: dict[str, str] = {}
    for r in rows:
        notes[str(r['date'])] = str(r['day_note'] or '')
    return MonthNotesResult(notes=notes)


@app.post('/api/uploads/images', response_model=GridImage)
def upload_image(date: str, file: UploadFile = File(...)) -> GridImage:
    date_key = parse_iso_date(date)
    ext = Path(file.filename or '').suffix.lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}:
        raise HTTPException(status_code=400, detail='지원하지 않는 이미지 형식입니다.')

    image_id = uuid.uuid4().hex
    filename = f'{image_id}{ext}'
    dest_path = UPLOAD_DIR / filename

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail='빈 파일입니다.')

    dest_path.write_bytes(data)

    width = 0
    height = 0
    try:
        with Image.open(dest_path) as img:
            width, height = img.size
    except Exception:
        width, height = 0, 0

    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO grid_images(id, day_date, filename, width, height, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (image_id, date_key, filename, width, height, utc_now_iso()),
        )

    base_url = os.getenv('PUBLIC_BASE_URL', '')
    url_path = f'/uploads/{filename}'
    url = f'{base_url}{url_path}' if base_url else url_path
    return GridImage(id=image_id, url=url, width=width, height=height)
