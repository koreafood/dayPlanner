# Proxmox 서버 배포 가이드 (Docker 미사용)

이 문서는 Proxmox 환경에서 VM 또는 LXC 컨테이너를 사용하여 본 프로젝트(dayPlanner)를 운영 배포하는 방법을 설명합니다. Docker를 사용하지 않고, Nginx + FastAPI(Uvicorn) + 정적 빌드(Vite)로 구성합니다.

## 구성 요소
- 프론트엔드: Vue 3 + TypeScript + Vite (정적 빌드 산출물 `dist/`)
- 백엔드: FastAPI + Uvicorn (SQLite DB: `api/app.db`, 업로드 디렉터리: `api/uploads/`)
- 웹 서버: Nginx (정적 파일 제공 및 `/api`, `/uploads` 리버스 프록시)

## 사전 준비
- Proxmox에 Ubuntu 22.04+ 기반의 VM 또는 LXC 컨테이너 생성
- 외부에서 접근 가능한 IP/도메인 준비(선택), 방화벽에서 80/443 포트 허용
- 서버 접속용 SSH 계정

## 1) 서버 생성(요약)
- VM: 일반적인 Ubuntu Server 설치 후 SSH 접근
- LXC: Ubuntu 템플릿으로 컨테이너 생성
  - 업로드 디렉터리 쓰기 권한을 위해 컨테이너 권한/마운트 설정을 확인
  - 성능/호환성을 위해 가능하면 privileged LXC 사용 또는 적절한 UID/GID 매핑

## 2) 필수 패키지 설치
```bash
sudo apt update
sudo apt install -y git curl nginx python3 python3-venv build-essential
```

Node.js가 필요합니다(프론트 빌드용). nvm 또는 배포 시점 한 번만 빌드할 계획이면 로컬에서 빌드 후 서버로 업로드해도 됩니다.
```bash
# nvm 설치 권장
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install --lts
nvm use --lts
node -v && npm -v
```

## 3) 코드 가져오기
```bash
sudo mkdir -p /opt/dayplanner
sudo chown -R $USER:$USER /opt/dayplanner
cd /opt/dayplanner
git clone https://github.com/koreafood/dayPlanner.git .
```

## 4) 프론트엔드 빌드
```bash
cd /opt/dayplanner
npm ci
npm run build
# 인쇄 페이지도 함께 배포
cp print.html dist/print.html
```

빌드 결과는 `/opt/dayplanner/dist`에 생성됩니다.

## 5) 백엔드 준비(가상환경)
```bash
cd /opt/dayplanner/api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

- 최초 실행 시 SQLite DB(`api/app.db`)와 업로드 디렉토리(`api/uploads`)가 자동 초기화됩니다.
- 퍼블릭 URL이 필요한 경우(이미지 URL 구성) 환경변수 `PUBLIC_BASE_URL`을 설정할 수 있습니다.

## 6) Systemd 서비스 등록(Uvicorn)
`/etc/systemd/system/dayplanner-api.service` 파일을 생성:
```ini
[Unit]
Description=DayPlanner FastAPI Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/dayplanner/api
Environment=PUBLIC_BASE_URL=https://your-domain.example
ExecStart=/opt/dayplanner/api/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8001 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

적용 및 기동:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dayplanner-api
sudo systemctl start dayplanner-api
sudo systemctl status dayplanner-api
```

업로드 디렉터리 권한이 필요한 경우:
```bash
sudo chown -R www-data:www-data /opt/dayplanner/api/uploads
```

## 7) Nginx 설정
새 서버 블록 생성(`/etc/nginx/sites-available/dayplanner`):
```nginx
server {
    listen 80;
    server_name your-domain.example;

    # 정적 프론트엔드
    root /opt/dayplanner/dist;
    index index.html;

    # SPA 라우팅
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 프린트 페이지
    location = /print.html {
        try_files /print.html =404;
    }

    # API 프록시
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 업로드 프록시(이미지 등)
    location /uploads {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

활성화 및 재기동:
```bash
sudo ln -s /etc/nginx/sites-available/dayplanner /etc/nginx/sites-enabled/dayplanner
sudo nginx -t
sudo systemctl reload nginx
```

## 8) HTTPS(선택)
도메인이 있다면 Certbot으로 TLS 적용:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.example
sudo systemctl reload nginx
```

## 9) 배포/업데이트 절차
```bash
cd /opt/dayplanner
git pull
npm ci
npm run build
cp print.html dist/print.html
sudo systemctl restart dayplanner-api
sudo systemctl reload nginx
```

## 10) 문제 해결 가이드
- 502 Bad Gateway: `dayplanner-api` 서비스 상태 확인(`systemctl status`), 포트/프록시 경로 점검
- 업로드 실패: `/opt/dayplanner/api/uploads` 권한 확인(웹 서버 사용자 쓰기 가능)
- CORS 오류: 프로덕션에서는 Nginx 경유로 동일 오리진 제공(개발용 프록시 설정은 Vite에서만 적용)
- 프론트 빌드 실패: Node.js 버전 확인(LTS), `npm ci` 재시도
- LXC 권한 문제: privileged 컨테이너 또는 적절한 마운트/UID/GID 매핑 사용

## 11) 운영 팁
- 백엔드 로그 확인: `journalctl -u dayplanner-api -f`
- Nginx 액세스/에러 로그: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- 백업: `/opt/dayplanner/api/app.db`, `/opt/dayplanner/api/uploads/` 주기적 백업

