#!/usr/bin/env bash
set -euo pipefail

# 배포 대상 서버의 주소 (필수)
SERVER_HOST=""
# 서버 접속 사용자 (기본값: ubuntu)
SERVER_USER="${SERVER_USER:-ubuntu}"
# 원격 서버에 배포할 루트 경로
REMOTE_PATH="${REMOTE_PATH:-/opt/dayplanner}"
# 서비스 도메인 (Nginx server_name 및 기본 PUBLIC_BASE_URL에 사용)
DOMAIN="${DOMAIN:-your-domain.example}"
# 백엔드 API가 바인딩될 포트
API_PORT="${API_PORT:-8001}"
# systemd 서비스 이름
SERVICE_NAME="${SERVICE_NAME:-dayplanner-api}"
# Nginx 사이트 이름 (설정 파일명에 사용)
SITE_NAME="${SITE_NAME:-dayplanner}"
# PUBLIC_BASE_URL 값을 직접 지정할 때 사용
PUBLIC_BASE_URL=""
# PUBLIC_BASE_URL이 CLI로 주어졌는지 여부
PUBLIC_BASE_URL_SET="false"
# HTTPS 자동 설정 여부
ENABLE_SSL="${ENABLE_SSL:-false}"
# certbot에 사용할 이메일
CERTBOT_EMAIL="${CERTBOT_EMAIL:-you@example.com}"
# 원격 sudo 비밀번호 (필요 시)
SUDO_PASS="${SUDO_PASS:-}"
# SSH 비밀번호 (키 대신 비밀번호 사용 시)
SSH_PASS="${SSH_PASS:-}"

# 옵션 파싱: 명령행 인자로 변수 재정의
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) SERVER_HOST="$2"; shift 2 ;;
    --user) SERVER_USER="$2"; shift 2 ;;
    --path) REMOTE_PATH="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --api-port) API_PORT="$2"; shift 2 ;;
    --service-name) SERVICE_NAME="$2"; shift 2 ;;
    --site-name) SITE_NAME="$2"; shift 2 ;;
    --public-base-url) PUBLIC_BASE_URL="$2"; PUBLIC_BASE_URL_SET="true"; shift 2 ;;
    --enable-ssl) ENABLE_SSL="$2"; shift 2 ;;
    --certbot-email) CERTBOT_EMAIL="$2"; shift 2 ;;
    --sudo-pass) SUDO_PASS="$2"; shift 2 ;;
    --ssh-pass) SSH_PASS="$2"; shift 2 ;;
    *) shift 1 ;;
  esac
done

# PUBLIC_BASE_URL 기본값 설정: 미지정 시 DOMAIN 기반으로 생성
if [[ "${PUBLIC_BASE_URL_SET}" != "true" ]]; then
  PUBLIC_BASE_URL="https://${DOMAIN}"
fi

# 필수 파라미터 확인: 서버 주소는 반드시 필요
if [[ -z "${SERVER_HOST}" ]]; then
  echo "사용법: scripts/deploy.sh --host <SERVER_HOST> [--user <USER>] [--path <REMOTE_PATH>] [--domain <DOMAIN>] [--api-port <PORT>] [--public-base-url <URL>] [--enable-ssl true|false] [--certbot-email <EMAIL>] [--sudo-pass <SUDO_PASSWORD>] [--ssh-pass <SSH_PASSWORD>]"
  exit 1
fi

# 프론트엔드 빌드 및 출력물 준비: 정적 자산 생성
echo "프론트엔드 빌드 시작"
npm ci
npm run build
cp print.html dist/print.html

# SSH/SCP 실행 방식 선택: 비밀번호 기반이면 sshpass 사용
remote="${SERVER_USER}@${SERVER_HOST}"
if [[ -n "${SSH_PASS}" ]]; then
  if ! command -v sshpass >/dev/null 2>&1; then
    echo "SSH 비밀번호를 사용하려면 로컬에 sshpass가 필요합니다."
    exit 1
  fi
  SSH_CMD=(sshpass -p "${SSH_PASS}" ssh -o StrictHostKeyChecking=accept-new)
  SCP_CMD=(sshpass -p "${SSH_PASS}" scp -o StrictHostKeyChecking=accept-new)
else
  SSH_CMD=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
  SCP_CMD=(scp -o StrictHostKeyChecking=accept-new)
fi

# sudo 비밀번호 전달용 이스케이프 함수: 싱글쿼트 안전 처리
escape_squote() {
  printf "%s" "$1" | sed "s/'/'\\\\''/g"
}

if [[ -n "${SUDO_PASS}" ]]; then
  SUDO_PASS_ESCAPED="$(escape_squote "${SUDO_PASS}")"
# sudo 명령을 비밀번호와 함께 실행하는 래퍼 함수 정의
  run_sudo() {
    "${SSH_CMD[@]}" "${remote}" "SUDO_PASS='${SUDO_PASS_ESCAPED}'; printf '%s' \"\$SUDO_PASS\" | sudo -S -p '' $1"
  }
fi

# SSH 연결 확인: 접속 실패 시 즉시 중단
if ! "${SSH_CMD[@]}" "${remote}" "true" >/dev/null 2>&1; then
  echo "SSH 인증에 실패했습니다. SSH 키를 설정하거나 --ssh-pass 옵션을 사용하세요."
  exit 1
fi

# 원격 사용자/그룹 확인: 서비스 소유권 설정에 사용
REMOTE_GROUP="$("${SSH_CMD[@]}" "${remote}" "id -gn '${SERVER_USER}'" 2>/dev/null || true)"
if [[ -z "${REMOTE_GROUP}" ]]; then
  echo "원격 사용자 그룹을 확인하지 못했습니다. 사용자 '${SERVER_USER}'가 존재하는지 확인하세요."
  exit 1
fi
# systemd 서비스 사용자/그룹 지정
SERVICE_USER="${SERVER_USER}"
SERVICE_GROUP="${REMOTE_GROUP}"

# sudo 권한 확인: 비밀번호 없는 sudo 가능 여부 검사
if [[ -z "${SUDO_PASS}" ]]; then
  if ! "${SSH_CMD[@]}" "${remote}" "sudo -n true" >/dev/null 2>&1; then
    echo "원격 sudo 비밀번호가 필요합니다. --sudo-pass 옵션을 사용하거나, 서버에서 NOPASSWD sudo를 설정하세요."
    exit 1
  fi
fi

# 원격 디렉터리 생성 및 소유권 설정: dist, api, uploads 준비
echo "원격 디렉터리 준비: ${REMOTE_PATH}"
if [[ -n "${SUDO_PASS}" ]]; then
  run_sudo "mkdir -p '${REMOTE_PATH}/dist' '${REMOTE_PATH}/api' '${REMOTE_PATH}/api/uploads' && sudo -S -p '' chown -R '${SERVER_USER}:${REMOTE_GROUP}' '${REMOTE_PATH}'"
else
  "${SSH_CMD[@]}" "${remote}" "sudo mkdir -p '${REMOTE_PATH}/dist' '${REMOTE_PATH}/api' '${REMOTE_PATH}/api/uploads' && sudo chown -R '${SERVER_USER}:${REMOTE_GROUP}' '${REMOTE_PATH}'"
fi

# 정적 파일 전송: 빌드 결과물 업로드
echo "정적 파일 전송"
"${SCP_CMD[@]}" -r dist/* "${remote}:${REMOTE_PATH}/dist/"
"${SCP_CMD[@]}" print.html "${remote}:${REMOTE_PATH}/dist/print.html"

# 백엔드 소스 및 의존성 파일 전송
echo "백엔드 코드 전송"
"${SCP_CMD[@]}" ./api/main.py "${remote}:${REMOTE_PATH}/api/main.py"
"${SCP_CMD[@]}" ./api/requirements.txt "${remote}:${REMOTE_PATH}/api/requirements.txt"

# 원격 서버 패키지 설치 및 파이썬 가상환경 구성
echo "서버 의존성 설치 및 가상환경 구성"
if [[ -n "${SUDO_PASS}" ]]; then
  run_sudo "apt-get update -y && sudo -S -p '' apt-get install -y python3 python3-venv nginx"
else
  "${SSH_CMD[@]}" "${remote}" "sudo apt-get update -y && sudo apt-get install -y python3 python3-venv nginx"
fi
"${SSH_CMD[@]}" "${remote}" "cd '${REMOTE_PATH}/api' && python3 -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt"

# 업로드 디렉터리 권한 부여: 파일 업로드 권한 확보
echo "업로드 디렉터리 권한 설정"
if [[ -n "${SUDO_PASS}" ]]; then
  run_sudo "chown -R '${SERVICE_USER}:${SERVICE_GROUP}' '${REMOTE_PATH}/api/uploads'"
else
  "${SSH_CMD[@]}" "${remote}" "sudo chown -R '${SERVICE_USER}:${SERVICE_GROUP}' '${REMOTE_PATH}/api/uploads'"
fi

# Systemd 서비스 유닛 생성 및 적용
echo "Systemd 서비스 생성"
UNIT="[Unit]
Description=DayPlanner FastAPI Service
After=network.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REMOTE_PATH}/api
Environment=PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
ExecStart=${REMOTE_PATH}/api/.venv/bin/uvicorn main:app --host 127.0.0.1 --port ${API_PORT} --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"
TMP_DIR="scripts/.deploy_tmp"
# 임시 디렉터리 생성: 서비스/NGINX 설정 파일 생성용
mkdir -p "${TMP_DIR}"
echo "$UNIT" > "${TMP_DIR}/${SERVICE_NAME}.service"
"${SCP_CMD[@]}" "${TMP_DIR}/${SERVICE_NAME}.service" "${remote}:~/${SERVICE_NAME}.service"
# 원격 서버에 systemd 유닛 배치 후 재시작
if [[ -n "${SUDO_PASS}" ]]; then
  run_sudo "mv ~/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service && sudo -S -p '' systemctl daemon-reload && sudo -S -p '' systemctl enable ${SERVICE_NAME} && sudo -S -p '' systemctl restart ${SERVICE_NAME}"
else
  "${SSH_CMD[@]}" "${remote}" "sudo mv ~/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service && sudo systemctl daemon-reload && sudo systemctl enable ${SERVICE_NAME} && sudo systemctl restart ${SERVICE_NAME}"
fi

# Nginx 가상호스트 설정 생성 및 적용
echo "Nginx 설정 생성"
NGINX_LOCAL="${TMP_DIR}/${SITE_NAME}.conf"
# 템플릿 치환: 도메인/경로/포트 반영
cat <<'NGINX_CONF' | sed -e "s|__DOMAIN__|${DOMAIN}|g" -e "s|__REMOTE_PATH__|${REMOTE_PATH}|g" -e "s|__API_PORT__|${API_PORT}|g" > "${NGINX_LOCAL}"
server {
    listen 80;
    server_name __DOMAIN__;

    root __REMOTE_PATH__/dist;
    index index.html;
    client_max_body_size 20M;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location = /print.html {
        try_files /print.html =404;
    }

    location /api {
        proxy_pass http://127.0.0.1:__API_PORT__;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads {
        proxy_pass http://127.0.0.1:__API_PORT__;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_CONF
"${SCP_CMD[@]}" "${NGINX_LOCAL}" "${remote}:~/${SITE_NAME}.conf"
# Nginx 설정 반영 및 재로드
if [[ -n "${SUDO_PASS}" ]]; then
  run_sudo "mv ~/${SITE_NAME}.conf /etc/nginx/sites-available/${SITE_NAME} && sudo -S -p '' ln -sf /etc/nginx/sites-available/${SITE_NAME} /etc/nginx/sites-enabled/${SITE_NAME} && sudo -S -p '' nginx -t && sudo -S -p '' systemctl reload nginx"
else
  "${SSH_CMD[@]}" "${remote}" "sudo mv ~/${SITE_NAME}.conf /etc/nginx/sites-available/${SITE_NAME} && sudo ln -sf /etc/nginx/sites-available/${SITE_NAME} /etc/nginx/sites-enabled/${SITE_NAME} && sudo nginx -t && sudo systemctl reload nginx"
fi

# 선택적으로 HTTPS 적용: certbot 자동 발급
if [[ "${ENABLE_SSL}" == "true" ]]; then
  echo "HTTPS 설정 적용"
  if [[ -n "${SUDO_PASS}" ]]; then
    run_sudo "apt-get install -y certbot python3-certbot-nginx"
    run_sudo "certbot --nginx -d ${DOMAIN} -m ${CERTBOT_EMAIL} --agree-tos --non-interactive || true"
    run_sudo "systemctl reload nginx"
  else
    "${SSH_CMD[@]}" "${remote}" "sudo apt-get install -y certbot python3-certbot-nginx"
    "${SSH_CMD[@]}" "${remote}" "sudo certbot --nginx -d ${DOMAIN} -m ${CERTBOT_EMAIL} --agree-tos --non-interactive || true"
    "${SSH_CMD[@]}" "${remote}" "sudo systemctl reload nginx"
  fi
fi

echo "배포 완료"
