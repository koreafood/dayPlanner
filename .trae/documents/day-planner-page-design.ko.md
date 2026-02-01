# 페이지 디자인 명세(Desktop-first)

## 공통(전역) 디자인
- Layout 시스템: Desktop 기준 12컬럼 그리드 + 섹션별 Flex 혼합. 상단 헤더 고정, 본문은 좌(달력) / 우(작업공간) 2단.
- 반응형: 
  - ≥1024px: 좌 320px(달력) + 우 유동(작업공간)
  - <1024px: 상단에 달력, 하단에 작업공간(1단 스택)
- Global Styles(토큰)
  - Background: #0B1220 (앱 배경), Surface: #111A2E (카드/패널)
  - Text: #E5E7EB, Muted: #9CA3AF
  - Accent: #4F46E5, Danger: #EF4444
  - Font: 시스템 폰트, base 14px, heading 18/20/24px
  - Button: 기본(Accent) / 보조(Surface) / 위험(Danger). Hover 시 밝기 +6%.
  - Input/textarea: radius 10px, border #24324F, focus outline Accent.

## 1) 플래너(홈) 페이지

### Meta Information
- Title: Day Planner
- Description: 날짜별 체크리스트와 메모를 저장/불러오기 하는 데일리 플래너
- Open Graph: og:title=Day Planner, og:description 동일, og:type=website

### Page Structure(데스크톱)
- 전체: `Header` + `Main(2단)`
- 좌측 패널(고정 폭): 달력 + 선택 날짜 요약
- 우측 작업공간(유동): 2행 구성
  - 상단: 저장/불러오기 상태 + 액션 버튼
  - 하단: 2열 그리드(좌: 체크박스/줄메모, 우: 메모판/모눈)

### Sections & Components
1. Header Bar
   - 좌: 앱명
   - 우: 현재 선택 날짜(YYYY-MM-DD) 배지

2. Left Panel: Calendar
   - 월/년 네비게이션(이전/다음)
   - 날짜 셀 클릭 시 선택 상태 강조(Accent 배경)
   - 오늘 날짜 표시(테두리)

3. Top Action Row(우측 상단)
   - 상태 표시: “불러오는 중/저장됨/저장 필요/오류”
   - 버튼: “불러오기”, “저장” (요구사항의 저장/불러오기를 명시적으로 제공)

4. 체크박스(할 일)
   - 리스트(체크박스 + 텍스트)
   - 하단 입력: 새 항목 추가(Enter)
   - 항목 삭제(휴지통 아이콘)

5. 줄메모
   - multiline textarea(가벼운 메모)
   - 글자 수가 늘어나면 자동 높이 확장(최대 높이 제한 후 스크롤)

6. 메모판
   - 큰 textarea(긴 메모)
   - 최소 높이 확보(예: 260px)

7. 모눈 메모(그리드 워크스페이스)
   - 캔버스/그리드 배경(모눈 라인: #24324F, 1px)
   - 블록(카드) 드래그 배치(텍스트 블록/이미지 블록)
   - 이미지 블록: 업로드 후 썸네일 표시, 클릭 시 원본 보기(모달)

8. 이미지 업로드(모눈 전용)
   - “이미지 업로드” 버튼 또는 드래그&드롭 영역
   - 업로드 중 진행 상태 표시(스피너/퍼센트)
   - 실패 시 재시도 버튼

### Interaction States
- 날짜 변경 시: 현재 편집 내용이 저장되지 않았으면 “저장 필요” 상태로 표시(저장 동작은 사용자가 수행)
- 저장 성공: 상태 “저장됨”, updatedAt 표시(선택)
- 업로드 성공: 반환된 이미지 URL로 즉시 미리보기 갱신
