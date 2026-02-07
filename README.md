# Vue 3 + TypeScript + Vite

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about the recommended Project Setup and IDE Support in the [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup).

## 데이터베이스 테이블 구조

SQLite 파일은 `api/app.db`이며, 서버 시작 시 테이블이 생성됩니다.

### day_entries

일별 플래너 데이터를 저장합니다.

| 컬럼 | 타입 | 제약/기본값 | 설명 |
| --- | --- | --- | --- |
| date | TEXT | PRIMARY KEY | 날짜(YYYY-MM-DD) |
| checklist_json | TEXT | NOT NULL DEFAULT '[]' | 체크리스트 JSON |
| line_memo | TEXT | NOT NULL DEFAULT '' | 시간대 메모 JSON 또는 텍스트 |
| board_memo | TEXT | NOT NULL DEFAULT '' | 보드 메모 |
| grid_json | TEXT | NOT NULL DEFAULT '{"cols":24,"rows":24,"blocks":[]}' | 그리드 JSON |
| updated_at | TEXT | NOT NULL | 마지막 저장 시간(UTC ISO) |
| day_note | TEXT | NOT NULL DEFAULT '' | 월간 메모용 노트 |

### grid_images

그리드에 추가된 이미지 메타데이터를 저장합니다.

| 컬럼 | 타입 | 제약/기본값 | 설명 |
| --- | --- | --- | --- |
| id | TEXT | PRIMARY KEY | 이미지 ID(UUID) |
| day_date | TEXT | NOT NULL | day_entries.date 참조용 날짜 |
| filename | TEXT | NOT NULL | 업로드된 파일명 |
| width | INTEGER | NOT NULL | 이미지 너비 |
| height | INTEGER | NOT NULL | 이미지 높이 |
| created_at | TEXT | NOT NULL | 생성 시간(UTC ISO) |

인덱스: `idx_grid_images_day_date`는 `grid_images(day_date)`에 생성됩니다.



# OpenSSH 설치/활성화
sudo apt update
sudo apt install -y openssh-server
sudo systemctl enable --now ssh