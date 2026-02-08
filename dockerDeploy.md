 # Proxmox 서버 배포 가이드 (Docker 사용)
 
 ## 개요
 - 목적: Proxmox 가상화 환경에서 Docker 워크로드를 안정적으로 배포하고 운영
 - 권장: Proxmox 호스트에는 Docker를 설치하지 않고, VM(우분투 등) 또는 LXC 컨테이너 내부에서 Docker를 실행
 - 선택지: VM 기반(가장 호환성 좋음, 권장) 또는 LXC 기반(가볍지만 제약 존재)
 
 ## 사전 준비
 - 하드웨어: VT-x/AMD-V 활성화, ECC 메모리 권장, SSD/NVMe
 - 네트워크: 고정 IP 또는 DHCP 예약, 필요시 VLAN/브리지 설계
 - 스토리지: ZFS(스냅샷/압축/RAID), 또는 LVM; 백업용 별도 스토리지/NAS 권장
 - ISO: Proxmox VE 최신 ISO, 게스트 OS(예: Ubuntu Server 24.04 LTS) ISO
 
 ## Proxmox 설치
 - ISO로 부팅 후 설치 진행, 파일 시스템은 ZFS(RAID1/RAIDZ) 권장
 - 관리 IP 설정, 호스트명과 DNS 구성
 - 설치 후 GUI 접속: `https://<proxmox-ip>:8006`
 - 최초 업데이트 및 구독 팝업 제거는 선택
 - 스토리지 확인: `local(local)`, `local-lvm(thin)`, 필요시 Datacenter → Storage에 NFS/CIFS 추가
 
 ## 네트워크 기본 구성
 - vmbr0 브리지에 물리 NIC 붙이고, 관리 IP를 vmbr0에 설정
 - 필요시 VLAN 활성화 및 추가 브리지(vmbr1 등) 정의
 - 방화벽: Datacenter / Node / VM 별로 활성화, 기본 정책 정리
 
 ## 아키텍처 선택 가이드
 - VM 기반 Docker(권장): 완전한 커널 격리, 시스템 업데이트/드라이버/도커 호환성 최고, 백업/스냅샷 용이
 - LXC 기반 Docker: 자원 효율 최고, 하지만 cgroup/권한/네트워크 등 제약과 호환성 이슈 가능
 - Proxmox 호스트에 Docker 설치는 비권장(가상화 호스트의 안정성과 격리 위협)
 
 ---
 
 ## 방법 A: VM 기반 Docker 배포(권장)
 
 ### 1) VM 생성
 - OS: Ubuntu Server 24.04 ISO
 - CPU/RAM: 워크로드에 맞게 할당(예: 4 vCPU, 8–32 GB RAM)
 - 디스크: virtio SCSI, SSD 에뮬레이션, 별도 데이터 디스크 추가 권장
 - 옵션: QEMU Agent 활성화, Display 비활성(헤드리스), Cloud-Init 사용 시 Drive 추가
 - 네트워크: vmbr0 연결, 필요시 고정 IP
 
 ### 2) 게스트 설치 후 에이전트 설치
 
 ```bash
 sudo apt update && sudo apt install -y qemu-guest-agent
 sudo systemctl enable --now qemu-guest-agent
 ```
 
 ### 3) Docker 설치(공식 CE + Compose 플러그인)
 
 ```bash
 sudo apt update
 sudo apt install -y ca-certificates curl gnupg
 sudo install -m 0755 -d /etc/apt/keyrings
 curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
 echo \
   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
   https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) stable" | \
   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
 
 sudo apt update
 sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
 
 sudo usermod -aG docker $USER
 # 재로그인 후 확인: docker run hello-world
 ```
 
 ### 4) 데이터 볼륨 설계
 - VM에 데이터용 추가 디스크(virtio) 생성 → 게스트에서 파티션/파일시스템 생성 → `/srv/docker` 같은 경로로 마운트
 - 또는 NAS(NFS/CIFS) 마운트로 외부 스토리지 사용
 
 ### 5) 예시: Traefik + Portainer Compose
 
 ```yaml
 # /srv/docker/compose/docker-compose.yml
 services:
   traefik:
     image: traefik:v3.0
     command:
       - --api.dashboard=true
       - --providers.docker=true
       - --entrypoints.web.address=:80
       - --entrypoints.websecure.address=:443
       - --certificatesresolvers.le.acme.httpchallenge=true
       - --certificatesresolvers.le.acme.httpchallenge.entrypoint=web
       - --certificatesresolvers.le.acme.email=you@example.com
       - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
     ports:
       - 80:80
       - 443:443
     volumes:
       - /var/run/docker.sock:/var/run/docker.sock:ro
       - ./letsencrypt:/letsencrypt
     restart: unless-stopped
 
   portainer:
     image: portainer/portainer-ce:latest
     command: -H unix:///var/run/docker.sock
     labels:
       - "traefik.enable=true"
       - "traefik.http.routers.portainer.rule=Host(`portainer.example.com`)"
       - "traefik.http.routers.portainer.tls.certresolver=le"
       - "traefik.http.services.portainer.loadbalancer.server.port=9000"
     volumes:
       - /var/run/docker.sock:/var/run/docker.sock
       - ./portainer:/data
     restart: unless-stopped
 ```
 
 ### 6) 배포/관리
 - 디렉터리 생성 후 `docker compose up -d`
 - Proxmox 스냅샷/백업(vzdump)로 VM 전체 보호
 - 게스트 내 Watchtower 등 자동 업데이트 도입은 선택
 
 ---
 
 ## Cloud-Init로 자동 프로비저닝(선택)
 - Proxmox에 Cloud-Init 드라이브 추가 후 user-data에 도커 설치 스크립트 포함
 
 ```yaml
 #cloud-config
 users:
   - name: dev
     groups: sudo
     shell: /bin/bash
     ssh_authorized_keys:
       - ssh-ed25519 AAAA... yourkey
 package_update: true
 runcmd:
   - apt-get update
   - apt-get install -y ca-certificates curl gnupg
   - install -m 0755 -d /etc/apt/keyrings
   - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   - echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
   - apt-get update
   - apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
   - usermod -aG docker dev
 ```
 
 ---
 
 ## 방법 B: LXC 기반 Docker 배포(경량)
 
 ### 1) LXC 생성
 - 템플릿: Ubuntu 24.04 또는 Debian 12
 - Privileged 컨테이너 권장(호환성↑), Unprivileged는 제약 존재
 - Rootfs는 충분한 공간, 네트워크 vmbr0, 고정 IP 선택 가능
 
 ### 2) 컨테이너 기능 설정
 - 옵션에서 Nesting 활성화
 - `/etc/pve/lxc/<CTID>.conf`에 기능 추가
 
 ```
 features: keyctl=1,nesting=1
 lxc.apparmor.profile: unconfined
 lxc.cgroup2.devices.allow: c 10:200 rwm
 lxc.mount.auto: "proc:rw sys:rw"
 ```
 
 ### 3) LXC 내부 Docker 설치(우분투 기준)
 
 ```bash
 apt update
 apt install -y ca-certificates curl gnupg
 install -m 0755 -d /etc/apt/keyrings
 curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
 echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
 apt update
 apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
 ```
 
 ### 4) 볼륨
 - 호스트 디렉터리를 LXC에 바인드 마운트(mp0 등)로 연결
 - 예: `mp0: /mnt/pve/data`, mp0 mount point: `/srv/docker`
 
 ### 5) 주의
 - Docker in LXC는 커널/권한/네트워크 제약으로 일부 이미지/드라이버가 비호환
 - 생산 환경에서는 VM 기반을 더 권장
 
 ---
 
 ## 네트워킹/도메인
 - 리버스 프록시(Traefik/Nginx)로 여러 컨테이너에 도메인/HTTPS 제공
 - Proxmox 방화벽에서 80/443 허용, 외부 라우터/NAT 포트 포워딩 설정
 - 내부 DNS 또는 Public DNS 레코드 관리
 
 ## 백업/복구 전략
 - VM 방식: Proxmox vzdump로 스냅샷/백업 + 주기적 이미지 보관
 - LXC 방식: 컨테이너 백업 + 바인드된 데이터 디렉터리(NAS 등) 별도 백업
 - 애플리케이션 레벨: DB 덤프/볼륨 스냅샷, Compose 디렉터리 Git 관리
 
 ## 모니터링/운영
 - Portainer로 Docker 관리
 - Proxmox Metrics/Graphs로 VM/LXC 자원 추적
 - 로깅: Loki/Promtail/Prometheus/Grafana 도입 고려
 
 ## 보안 체크리스트
 - Proxmox/게스트 OS 정기 업데이트
 - SSH 키 기반 접근, 비밀번호 로그인 제한
 - 방화벽 정책 최소 권한, 외부 노출 포트 절감
 - Traefik/Nginx에서 강제 HTTPS 및 보안 헤더 적용
 
 ## 문제 해결 팁
 - VM 네트워크 끊김: virtio NIC, QEMU Agent 확인, 브리지/VLAN 재검토
 - LXC에서 Docker 데몬 오류: nesting, apparmor, cgroup v2 설정 재확인
 - 퍼포먼스: CPU 핀닝, HugePages, I/O 스케줄러, ZFS 압축 조정
 - 저장소: overlay2 스토리지 드라이버 사용, 권한/SELinux/AppArmor 제약 점검
 
 ## 최소 실행 예시(요약)
 - VM 만들기 → Ubuntu 설치 → QEMU Agent 설치 → Docker 설치 → Compose로 Traefik/Portainer 실행 → Proxmox 백업 스케줄링
 
 ```bash
 mkdir -p /srv/docker/compose && cd /srv/docker/compose
 docker compose up -d
 ```
 
 ---
 
 ## 참고
 - 원하는 구성(도메인, 서비스 목록, NAS 여부)을 알려주시면 Cloud-Init user-data와 Compose 템플릿을 맞춤 제공할 수 있습니다.

---

## 배포 자동화(sshpass 사용)

### 개요
- SSH가 비밀번호 기반인 환경에서 자동 배포를 위해 `sshpass`를 사용하면 비대화식으로 SSH/Scp를 수행할 수 있습니다.
- 본 프로젝트의 `scripts/deploy.sh`는 `--ssh-pass`(SSH 비밀번호)와 `--sudo-pass`(원격 sudo 비밀번호)를 각각 받아 안전하게 자동화를 수행합니다.

### 설치
- macOS(Homebrew):
```bash
brew install sshpass
```
- Debian/Ubuntu:
```bash
sudo apt update
sudo apt install -y sshpass
```
- RHEL/CentOS(패키지 가용성에 따라 달라질 수 있음):
```bash
sudo yum install -y epel-release
sudo yum install -y sshpass
```

### 사용 예시
```bash
scripts/deploy.sh \
  --host 192.168.0.62 \
  --user ubuntu \
  --path /opt/dayplanner \
  --domain dp.lala.dedyn.io \
  --ssh-pass '<SSH_비밀번호>' \
  --sudo-pass '<SUDO_비밀번호>'
```

### 보안 권장
- 가능하면 SSH 키 기반 인증을 사용하고, 서버에서 배포 사용자에 대해 특정 명령(Nginx/Service 관리)에 한정된 NOPASSWD sudo를 설정하면 보다 안전하고 간편합니다.
- 비밀번호를 스크립트 인자로 직접 넣기보다, 환경 변수로 전달하는 방법을 고려하세요:
```bash
SSH_PASS='<SSH_비밀번호>' SUDO_PASS='<SUDO_비밀번호>' \
scripts/deploy.sh --host 192.168.0.62 --domain dp.lala.dedyn.io
```
