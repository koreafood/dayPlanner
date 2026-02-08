# 타입 힌트에서 미래 기능(PEP 563/649 스타일)을 사용하기 위한 선언
from __future__ import annotations

import json  # JSON 직렬화/역직렬화
import os  # 환경 변수 접근, 경로 처리
import sqlite3  # 내장 SQLite 데이터베이스
import uuid  # 고유 ID 생성
from datetime import datetime, timezone  # 시간/타임존 처리
from pathlib import Path  # 경로 객체화
from typing import Any, Literal  # 타입 힌트 유틸리티
from urllib.error import HTTPError  # HTTP 오류 타입
from urllib.parse import urlencode  # 쿼리스트링 생성
from urllib.request import Request as UrlRequest, urlopen  # HTTP 요청/응답

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile  # FastAPI 핵심
from fastapi.middleware.cors import CORSMiddleware  # CORS 처리
from fastapi.staticfiles import StaticFiles  # 정적 파일 서빙
from pydantic import BaseModel, Field  # 데이터 검증 모델
from PIL import Image  # 이미지 정보 추출


def utc_now_iso() -> str:
    """현재 UTC 시각을 ISO 8601 문자열로 반환"""
    return datetime.now(timezone.utc).isoformat()


def parse_iso_date(date_str: str) -> str:
    """YYYY-MM-DD 형식의 문자열을 검증하고 동일 형식으로 반환"""
    try:
        # fromisoformat은 날짜/시간 모두 허용하므로 date()만 추출하여 일자만 사용
        return datetime.fromisoformat(date_str).date().isoformat()
    except Exception:
        # 형식 오류 시 400 반환
        raise HTTPException(status_code=400, detail='date는 YYYY-MM-DD 형식이어야 합니다.')


def fetch_upstream_json(url: str) -> Any:
    """업스트림(Open-Meteo 등) API에서 JSON 응답을 받아 파싱"""
    req = UrlRequest(url, headers={"User-Agent": "dayplanner"})  # 간단한 UA 설정
    try:
        with urlopen(req, timeout=10) as res:  # 타임아웃 10초
            raw = res.read()  # 바이트 읽기
    except HTTPError as e:
        # 업스트림이 반환한 상태코드 그대로 전달
        raise HTTPException(status_code=e.code, detail='날씨 API 오류')
    except Exception:
        # 네트워크/타임아웃 등 일반 오류
        raise HTTPException(status_code=502, detail='날씨 API 요청 실패')
    try:
        return json.loads(raw)  # JSON 파싱
    except Exception:
        # 비정상 응답 본문
        raise HTTPException(status_code=502, detail='날씨 API 응답 파싱 실패')


def resolve_public_base_url(request: Request) -> str:
    """외부에서 접근 가능한 베이스 URL을 결정
    - 환경변수 PUBLIC_BASE_URL 우선 사용(특정 도메인 제외 규칙 포함)
    - 프록시 헤더(x-forwarded-*) 또는 요청 URL 스킴/호스트 기반 추론
    """
    base_url = os.getenv('PUBLIC_BASE_URL', '').strip()  # 환경변수에서 읽음
    if base_url and 'dp.lala.dedyn.io' not in base_url:  # 특정 도메인일 경우 우회 허용 규칙
        return base_url.rstrip('/')  # 슬래시 정규화
    proto = request.headers.get('x-forwarded-proto') or request.url.scheme  # 스킴 추론
    host = request.headers.get('x-forwarded-host') or request.headers.get('host')  # 호스트 추론
    if host:
        return f'{proto}://{host}'  # 완전한 베이스 URL 구성
    return base_url.rstrip('/')  # 최종 폴백


BASE_DIR = Path(__file__).resolve().parent  # 현재 파일 기준 기본 디렉터리
DB_PATH = BASE_DIR / 'app.db'  # SQLite DB 파일 경로
UPLOAD_DIR = BASE_DIR / 'uploads'  # 업로드 파일 저장 디렉터리
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # 디렉터리 생성(존재해도 OK)


def db_connect() -> sqlite3.Connection:
    """SQLite 커넥션 생성(Row를 dict처럼 접근 가능하도록 설정)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 컬럼명을 키로 접근 가능
    return conn


def db_init() -> None:
    """데이터베이스 초기화(테이블/인덱스 생성 및 스키마 마이그레이션)"""
    with db_connect() as conn:
        # 메인 일자 엔트리 테이블
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

        # 스키마 점검: day_note 컬럼 없으면 추가
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(day_entries)").fetchall()}
        if "day_note" not in cols:
            conn.execute("ALTER TABLE day_entries ADD COLUMN day_note TEXT NOT NULL DEFAULT ''")
        # 그리드 이미지 메타 테이블
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
        # 조회 최적화 인덱스
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_grid_images_day_date
            ON grid_images(day_date);
            """
        )


class ChecklistItem(BaseModel):
    """체크리스트 항목"""
    id: str  # 고유 ID
    text: str  # 본문
    checked: bool  # 체크 여부
    order: int  # 표시 순서
    note: str = ''  # 부가 메모


class ScheduleMemo(BaseModel):
    """시간대 일정 메모"""
    hour: int = Field(ge=0, le=23)  # 0~23시
    text: str = ''  # 메모


class GridImage(BaseModel):
    """그리드에 표시할 이미지 메타"""
    id: str  # 이미지 ID
    url: str  # 접근 URL
    width: int  # 가로
    height: int  # 세로


class GridBlock(BaseModel):
    """그리드의 단일 블록(텍스트/이미지)"""
    id: str  # 블록 ID
    x: float  # 좌표 X(px)
    y: float  # 좌표 Y(px)
    w: float  # 너비(px)
    h: float  # 높이(px)
    type: Literal['text', 'image']  # 타입
    text: str | None = None  # 텍스트 내용
    image: GridImage | None = None  # 이미지 메타


class GridPayload(BaseModel):
    """그리드 전체 상태"""
    cols: int = 24  # 컬럼 수(표시용)
    rows: int = 24  # 로우 수(표시용)
    blocks: list[GridBlock] = Field(default_factory=list)  # 블록 목록


class DayPayload(BaseModel):
    """단일 날짜 데이터 페이로드"""
    date: str  # ISO 날짜
    checklist: list[ChecklistItem] = Field(default_factory=list)  # 체크리스트
    dayNote: str = ''  # 달력에 표시될 한 줄 메모
    scheduleMemos: list[ScheduleMemo] = Field(default_factory=list)  # 일정 메모
    boardMemo: str = ''  # 자유 메모
    grid: GridPayload = Field(default_factory=GridPayload)  # 그리드 상태
    updatedAt: str  # 마지막 갱신 시각


class SaveResult(BaseModel):
    """저장 결과 응답"""
    ok: bool  # 성공 여부
    updatedAt: str  # 갱신 시각


class MonthNotesResult(BaseModel):
    """월별 노트 응답: 날짜→메모"""
    notes: dict[str, str]


app = FastAPI()  # 애플리케이션 인스턴스 생성

app.add_middleware(
    CORSMiddleware,  # 개발 환경에서 프론트엔드 접근 허용
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
def on_startup() -> None:
    """서버 시작 시 DB 초기화"""
    db_init()


app.mount('/uploads', StaticFiles(directory=str(UPLOAD_DIR)), name='uploads')  # 이미지 정적 서빙


def day_default(date_str: str) -> DayPayload:
    """DB에 없을 때 기본 일자 페이로드 생성"""
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
    """단일 날짜 데이터 조회"""
    date_key = parse_iso_date(date)  # 경로 파라미터 검증
    with db_connect() as conn:
        row = conn.execute('SELECT * FROM day_entries WHERE date = ?', (date_key,)).fetchone()  # 단건 조회

    if row is None:
        return day_default(date_key)  # 없으면 기본값 반환

    # 체크리스트 JSON 파싱
    try:
        checklist = json.loads(row['checklist_json'] or '[]')
    except Exception:
        checklist = []

    # 일정 메모 역호환 처리(line_memo는 문자열/JSON 모두 가능)
    schedule_memos: list[dict] = []
    raw_schedule = row['line_memo'] or ''
    if raw_schedule:
        try:
            parsed = json.loads(raw_schedule)
            if isinstance(parsed, list):
                schedule_memos = parsed
        except Exception:
            # 줄바꿈 기반 텍스트를 시간과 매칭하여 변환
            lines = [x for x in str(raw_schedule).split('\n')]
            schedule_memos = [
                {"hour": min(i, 23), "text": line}
                for i, line in enumerate(lines)
                if line is not None
            ]

    # 그리드 JSON 파싱(기본값 폴백)
    try:
        grid = json.loads(row['grid_json'] or '{"cols":24,"rows":24,"blocks":[]}')
    except Exception:
        grid = {"cols": 24, "rows": 24, "blocks": []}

    # 최종 페이로드 구성
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
    """단일 날짜 데이터 저장/업데이트(UPSERT)"""
    date_key = parse_iso_date(date)  # 경로 파라미터 검증
    body_key = parse_iso_date(payload.date)  # 바디 검증
    if date_key != body_key:
        # 경로와 바디의 날짜가 다르면 오류
        raise HTTPException(status_code=400, detail='path date와 body date가 일치해야 합니다.')

    updated_at = utc_now_iso()  # 갱신 시각
    # 리스트/객체들을 JSON 문자열로 직렬화
    checklist_json = json.dumps([i.model_dump() for i in payload.checklist], ensure_ascii=False)
    schedule_json = json.dumps([i.model_dump() for i in payload.scheduleMemos], ensure_ascii=False)
    grid_json = json.dumps(payload.grid.model_dump(), ensure_ascii=False)

    # UPSERT 수행
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

    return SaveResult(ok=True, updatedAt=updated_at)  # 결과 반환


@app.get('/api/month-notes', response_model=MonthNotesResult)
def get_month_notes(year: int, month: int) -> MonthNotesResult:
    """해당 월의 day_note만 모아 반환"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail='month는 1~12 범위여야 합니다.')
    start = datetime(year, month, 1).date().isoformat()  # 월 시작
    if month == 12:
        end = datetime(year + 1, 1, 1).date().isoformat()  # 다음 해 1월
    else:
        end = datetime(year, month + 1, 1).date().isoformat()  # 다음 달 1일

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
        notes[str(r['date'])] = str(r['day_note'] or '')  # 문자열로 정규화
    return MonthNotesResult(notes=notes)


@app.get('/api/weather/forecast')
def get_weather_forecast(
    latitude: float,
    longitude: float,
    daily: str = Query('weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max'),
    timezone: str = Query('auto'),
    forecast_days: int | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> Any:
    """Open-Meteo 예보 API 프록시"""
    params: dict[str, str] = {
        'latitude': str(latitude),
        'longitude': str(longitude),
        'daily': daily,
        'timezone': timezone,
    }
    if forecast_days is not None:
        params['forecast_days'] = str(forecast_days)
    if start_date is not None:
        params['start_date'] = start_date
    if end_date is not None:
        params['end_date'] = end_date
    url = f"https://api.open-meteo.com/v1/forecast?{urlencode(params)}"
    return fetch_upstream_json(url)


@app.get('/api/weather/geocode')
def get_weather_geocode(
    name: str,
    count: int = Query(8, ge=1, le=20),
    language: str = Query('ko'),
    format: str = Query('json'),
) -> Any:
    """Open-Meteo 지오코딩 검색 프록시"""
    params = {'name': name, 'count': str(count), 'language': language, 'format': format}
    url = f"https://geocoding-api.open-meteo.com/v1/search?{urlencode(params)}"
    return fetch_upstream_json(url)


@app.get('/api/weather/reverse')
def get_weather_reverse(
    latitude: float,
    longitude: float,
    language: str = Query('ko'),
    format: str = Query('json'),
) -> Any:
    """Open-Meteo 역지오코딩 프록시"""
    params = {
        'latitude': str(latitude),
        'longitude': str(longitude),
        'language': language,
        'format': format,
    }
    url = f"https://geocoding-api.open-meteo.com/v1/reverse?{urlencode(params)}"
    return fetch_upstream_json(url)


@app.post('/api/uploads/images', response_model=GridImage)
def upload_image(request: Request, date: str, file: UploadFile = File(...)) -> GridImage:
    """이미지 업로드 후 메타를 반환하고 정적 경로로 접근 가능하게 함"""
    date_key = parse_iso_date(date)  # 날짜 검증
    ext = Path(file.filename or '').suffix.lower()  # 확장자 추출
    if ext not in {'.png', '.jpg', '.jpeg', '.webp', '.gif'}:
        raise HTTPException(status_code=400, detail='지원하지 않는 이미지 형식입니다.')

    image_id = uuid.uuid4().hex  # 고유 이미지 ID
    filename = f'{image_id}{ext}'  # 파일명 구성
    dest_path = UPLOAD_DIR / filename  # 저장 경로

    data = file.file.read()  # 파일 바이트 읽기
    if not data:
        raise HTTPException(status_code=400, detail='빈 파일입니다.')

    dest_path.write_bytes(data)  # 파일 저장

    width = 0
    height = 0
    try:
        with Image.open(dest_path) as img:  # Pillow로 크기 확인
            width, height = img.size
    except Exception:
        width, height = 0, 0  # 실패 시 0으로 폴백

    # 이미지 메타 DB에 저장
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO grid_images(id, day_date, filename, width, height, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (image_id, date_key, filename, width, height, utc_now_iso()),
        )

    base_url = resolve_public_base_url(request)  # 접근 가능한 베이스 URL
    url_path = f'/uploads/{filename}'  # 정적 경로
    url = f'{base_url}{url_path}' if base_url else url_path  # 절대/상대 URL 구성
    return GridImage(id=image_id, url=url, width=width, height=height)
