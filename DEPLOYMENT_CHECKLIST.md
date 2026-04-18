# ✅ Google Cloud 배포 체크리스트

Google Cloud VM에 Discord 봇을 배포하기 전 확인해야 할 항목들입니다.

---

## 🔐 토큰 및 보안

- [ ] Discord Bot Token 획득
  - [ ] [Discord Developer Portal](https://discord.com/developers/applications) 접속
  - [ ] 애플리케이션 생성
  - [ ] Bot 탭에서 TOKEN 복사
  - [ ] 토큰을 안전하게 보관 (절대 Git에 커밋 금지!)

- [ ] Discord Bot 권한 설정
  - [ ] Privileged Gateway Intents 활성화
    - [ ] PRESENCE INTENT
    - [ ] SERVER MEMBERS INTENT
    - [ ] MESSAGE CONTENT INTENT
  - [ ] OAuth2 URL 생성
    - [ ] Scopes: `bot`, `applications.commands` 선택
    - [ ] Permissions 설정:
      - [ ] Send Messages
      - [ ] Embed Links
      - [ ] Manage Channels
      - [ ] Manage Roles
      - [ ] Manage Guild

- [ ] Discord 서버에 봇 추가
  - [ ] OAuth2 URL로 서버에 봇 추가
  - [ ] 봇에 관리자 권한 부여 (테스트 시)

---

## ☁️ Google Cloud 설정

- [ ] Google Cloud 프로젝트 생성
  - [ ] [Google Cloud Console](https://console.cloud.google.com) 접속
  - [ ] 프로젝트 생성
  - [ ] Billing 활성화 (또는 항상 무료 한도 사용)

- [ ] VM 인스턴스 생성
  - [ ] Compute Engine → VM 인스턴스
  - [ ] 인스턴스 생성:
    - [ ] 이름: `discord-bot` (예)
    - [ ] Region: `us-central1` (항상 무료 한도)
    - [ ] Zone: `us-central1-a`
    - [ ] Machine type: `e2-micro` (항상 무료)
    - [ ] Image: `Ubuntu 22.04 LTS`
    - [ ] Boot disk: 30GB (기본값)
  - [ ] 방화벽 설정: 기본값 (봇은 웹 포트 사용 안 함)

- [ ] SSH 키 설정 (선택사항)
  - [ ] OS login 활성화
  - [ ] SSH 공개키 추가

---

## 💻 로컬 준비

- [ ] 프로젝트 파일 준비
  - [ ] 모든 Python 파일 확인
  - [ ] 모든 설정 파일 확인
  - [ ] requirements.txt 확인

- [ ] .env 파일 준비
  - [ ] .env.example → .env 복사
  - [ ] DISCORD_TOKEN 추가
  - [ ] ALLOWED_USER_IDS 추가

- [ ] Git 저장소 준비 (선택사항)
  - [ ] GitHub에 코드 푸시
  - [ ] .env, settings.json은 .gitignore에 포함
  - [ ] README.md 작성

---

## 🚀 VM 배포

### 파일 업로드

- [ ] 프로젝트 파일 VM에 업로드
  - [ ] 방법 선택:
    - [ ] Cloud Storage 사용
    - [ ] GitHub에서 git clone
    - [ ] SCP로 직접 업로드
  - [ ] ~/Akitect 경로에 배치

### 배포 스크립트 실행

- [ ] deploy.sh 실행
  ```bash
  cd ~/Akitect
  chmod +x deploy.sh
  ./deploy.sh
  ```

- [ ] 배포 과정 확인
  - [ ] Python 설치 확인
  - [ ] 가상환경 생성
  - [ ] 패키지 설치
  - [ ] .env 파일 확인
  - [ ] 봇 테스트 실행
  - [ ] Systemd 서비스 설정

### 수동 배포 (선택)

deploy.sh 사용 안 하는 경우:

- [ ] 기본 패키지 설치
  ```bash
  sudo apt update && sudo apt upgrade -y
  sudo apt install -y python3-venv python3-dev git
  ```

- [ ] 가상환경 생성
  ```bash
  cd ~/Akitect
  python3 -m venv venv
  source venv/bin/activate
  ```

- [ ] 패키지 설치
  ```bash
  pip install -r requirements.txt
  ```

- [ ] .env 파일 생성
  ```bash
  nano .env
  # DISCORD_TOKEN=...
  # ALLOWED_USER_IDS=...
  ```

- [ ] 봇 테스트
  ```bash
  python main.py
  # Ctrl+C로 중지
  ```

- [ ] Systemd 서비스 설정
  ```bash
  sudo nano /etc/systemd/system/discord-bot.service
  # 파일 내용은 GOOGLE_CLOUD_SETUP.md 참고
  
  sudo systemctl daemon-reload
  sudo systemctl enable discord-bot
  sudo systemctl start discord-bot
  ```

---

## 🧪 테스트

### 봇 시작 확인

- [ ] 서비스 상태 확인
  ```bash
  sudo systemctl status discord-bot
  ```

- [ ] 로그 확인
  ```bash
  sudo journalctl -u discord-bot -n 20
  ```

- [ ] "로그인 성공" 메시지 확인
  ```bash
  sudo journalctl -u discord-bot | grep "로그인 성공"
  ```

### Discord 명령어 테스트

- [ ] 명령어 동기화
  ```
  /동기화 → ✅ 동기화 완료
  ```

- [ ] 기본 명령어 테스트
  ```
  /템플릿목록 → 응답 확인
  /도움 → 응답 확인
  ```

- [ ] 실제 기능 테스트
  ```
  /템플릿생성
  → 템플릿 생성 확인
  
  /템플릿목록
  → 생성한 템플릿 표시 확인
  ```

---

## 📊 모니터링

### 정기적인 확인

- [ ] 일일: 로그에서 에러 확인
  ```bash
  sudo journalctl -u discord-bot | grep ERROR
  ```

- [ ] 주간: 봇 상태 확인
  ```bash
  sudo systemctl status discord-bot
  ```

- [ ] 월간: 디스크 사용량 확인
  ```bash
  du -sh ~/Akitect
  ```

### 자동 모니터링 (선택)

- [ ] Uptime Robot 설정 (선택사항)
  - [ ] https://uptimerobot.com 가입
  - [ ] 모니터링 URL 추가
  - [ ] 알림 설정

---

## 🔄 유지보수

### 정기적인 업데이트

- [ ] 매월: 시스템 업데이트
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```

- [ ] 필요시: 봇 코드 업데이트
  ```bash
  cd ~/Akitect
  git pull origin main
  pip install -r requirements.txt
  sudo systemctl restart discord-bot
  ```

### 백업

- [ ] 주간: 설정 파일 백업
  ```bash
  tar -czf ~/backup-$(date +%Y%m%d).tar.gz ~/Akitect/settings.json
  ```

- [ ] settings.json을 Cloud Storage에 백업 (선택사항)

---

## 🆘 트러블슈팅

### 봇이 시작되지 않으면

- [ ] 로그 확인
  ```bash
  sudo journalctl -u discord-bot -n 50
  ```

- [ ] .env 파일 확인
  ```bash
  cat ~/Akitect/.env
  ```

- [ ] 토큰 유효성 확인
  - [ ] Discord Developer Portal에서 토큰 재발급

### 높은 CPU/메모리 사용

- [ ] 프로세스 확인
  ```bash
  ps aux | grep "python main.py"
  ```

- [ ] 메모리 사용 확인
  ```bash
  free -h
  ```

- [ ] 봇 재시작
  ```bash
  sudo systemctl restart discord-bot
  ```

### 명령어가 작동하지 않음

- [ ] Discord에서 명령어 동기화
  ```
  /동기화
  ```

- [ ] 로그에서 에러 확인
  ```bash
  sudo journalctl -u discord-bot | grep ERROR
  ```

---

## 💾 설정 보관

### 중요 정보 기록

- [ ] Discord Bot Token: `_________________`
- [ ] Google Cloud Project ID: `_________________`
- [ ] VM 인스턴스 IP: `_________________`
- [ ] VM 인스턴스 이름: `_________________`
- [ ] SSH 접속 방법: `_________________`

**⚠️ 주의: 이 정보는 안전하게 보관하세요!**

---

## 📚 참고 문서

- 📖 [README.md](./README.md) - 사용 설명서
- 🚀 [QUICK_DEPLOY.md](./QUICK_DEPLOY.md) - 빠른 배포 가이드
- ☁️ [GOOGLE_CLOUD_SETUP.md](./GOOGLE_CLOUD_SETUP.md) - 상세 설정 가이드

---

## ✨ 배포 완료 확인

모든 항목을 확인했으면:

- ✅ 봇이 Google Cloud에서 24/7 실행 중
- ✅ Discord 서버에서 명령어 사용 가능
- ✅ 로그 모니터링 가능
- ✅ 자동 재시작 설정 완료

**축하합니다!** 🎉

---

**마지막 확인 날짜**: ________________
**배포 담당자**: ________________
