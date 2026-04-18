# 🚀 Google Cloud VM에서 Discord 봇 호스팅하기

Ubuntu 22.04 LTS Google Cloud VM 인스턴스에서 Discord 봇을 24/7 운영하는 완벽한 가이드입니다.

---

## 📋 목차

1. [VM 접속](#vm-접속)
2. [환경 설정](#환경-설정)
3. [봇 배포](#봇-배포)
4. [백그라운드 실행](#백그라운드-실행)
5. [모니터링 및 유지보수](#모니터링-및-유지보수)
6. [트러블슈팅](#트러블슈팅)

---

## 🔑 VM 접속

### 1. SSH로 VM 접속

#### 방법 1: Cloud Console에서 직접 접속 (추천)

```
Google Cloud Console
↓
Compute Engine → VM 인스턴스
↓
인스턴스 선택 → 🔗 SSH 클릭
```

#### 방법 2: gcloud CLI로 접속

```bash
gcloud compute ssh akitect-bot --zone=us-central1-a
```

---

## ⚙️ 환경 설정

### 1. 시스템 업데이트

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Python 3.10+ 설치

```bash
# 확인
python3 --version

# Python 3.10 이상이 설치되어 있다면 다음 스텝으로 진행
# 없으면 설치
sudo apt install -y python3.10 python3.10-venv python3.10-dev
```

### 3. 필수 패키지 설치

```bash
sudo apt install -y git curl wget nano
```

### 4. 프로젝트 디렉토리 생성

```bash
# 홈 디렉토리로 이동
cd ~

# 프로젝트 폴더 생성
mkdir -p /home/discord-bot
cd /home/discord-bot
```

---

## 📦 봇 배포

### 1. 프로젝트 파일 업로드

#### 방법 1: Cloud Storage를 통해 업로드 (추천)

```bash
# 로컬 머신에서
# 1. Cloud Console → Cloud Storage → Bucket 생성
# 2. Akitect 폴더 전체 업로드
# 3. VM에서 다운로드

gsutil -m cp -r gs://your-bucket-name/Akitect /home/discord-bot/
```

#### 방법 2: Git으로 복제

```bash
# GitHub에 푸시했다면
git clone https://github.com/your-username/Akitect.git /home/discord-bot/Akitect
```

#### 방법 3: SCP로 업로드

```bash
# 로컬 머신에서
scp -r ./Akitect google_account@vm-ip:/home/discord-bot/
```

### 2. 가상환경 생성 및 패키지 설치

```bash
cd /home/discord-bot/Akitect

# 가상환경 생성
python3 -m venv venv

# 활성화
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
# .env 파일 생성
nano .env
```

파일 내용:
```env
DISCORD_TOKEN=your_token_here
ALLOWED_USER_IDS=343290913172226049
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

### 4. 봇 테스트 실행

```bash
# 가상환경 활성화 확인
which python  # venv 경로가 나와야 함

# 봇 실행
python main.py
```

성공 메시지:
```
✅ 로그인 성공: Akitect#1234
```

`Ctrl+C`로 중지

---

## 🔄 백그라운드 실행

봇을 24/7 실행하려면 다음 중 하나를 선택:

### 방법 1: Systemd 서비스 (⭐ 추천)

가장 안정적이고 추천하는 방법입니다.

#### 1. 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/discord-bot.service
```

파일 내용:
```ini
[Unit]
Description=Discord Bot (Akitect)
After=network.target

[Service]
Type=simple
User=debian
WorkingDirectory=/home/discord-bot/Akitect
Environment="PATH=/home/discord-bot/Akitect/venv/bin"
ExecStart=/home/discord-bot/Akitect/venv/bin/python main.py

# 자동 재시작
Restart=always
RestartSec=10

# 로깅
StandardOutput=append:/home/discord-bot/Akitect/bot.log
StandardError=append:/home/discord-bot/Akitect/error.log

[Install]
WantedBy=multi-user.target
```

#### 2. 서비스 활성화 및 시작

```bash
# 서비스 재로드
sudo systemctl daemon-reload

# 자동 시작 활성화
sudo systemctl enable discord-bot

# 서비스 시작
sudo systemctl start discord-bot

# 상태 확인
sudo systemctl status discord-bot
```

#### 3. 로그 확인

```bash
# 실시간 로그
sudo journalctl -u discord-bot -f

# 최근 100줄
sudo journalctl -u discord-bot -n 100
```

---

### 방법 2: Screen 사용

간단하지만 수동 관리 필요:

```bash
# screen 설치
sudo apt install -y screen

# screen 세션 시작
screen -S discord-bot

# 가상환경 활성화
cd /home/discord-bot/Akitect
source venv/bin/activate

# 봇 실행
python main.py

# 백그라운드로 보내기
Ctrl+A → D
```

관리:
```bash
# 세션 목록
screen -ls

# 세션 재진입
screen -r discord-bot

# 세션 종료
screen -S discord-bot -X quit
```

---

### 방법 3: Nohup 사용

가장 간단한 방법:

```bash
cd /home/discord-bot/Akitect

# 백그라운드 실행
nohup python main.py > bot.log 2>&1 &

# PID 확인
ps aux | grep "python main.py"

# 프로세스 종료 (필요시)
kill -9 <PID>
```

---

## 📊 모니터링 및 유지보수

### 1. 로그 확인

```bash
# 실시간 로그
tail -f /home/discord-bot/Akitect/bot.log

# 에러만 보기
grep "ERROR" /home/discord-bot/Akitect/bot.log

# 마지막 50줄
tail -n 50 /home/discord-bot/Akitect/bot.log
```

### 2. 봇 상태 확인

```bash
# 프로세스 실행 중?
ps aux | grep "python main.py"

# 포트 사용? (Discord API는 특정 포트 사용 안 함)
lsof -i -P -n | grep LISTEN
```

### 3. 봇 재시작

**Systemd 사용 시:**
```bash
sudo systemctl restart discord-bot
```

**Screen 사용 시:**
```bash
screen -S discord-bot -X quit
cd /home/discord-bot/Akitect && source venv/bin/activate && python main.py
```

### 4. 정기적인 업데이트

```bash
cd /home/discord-bot/Akitect

# 코드 업데이트
git pull origin main

# 새 의존성 설치
source venv/bin/activate
pip install -r requirements.txt

# 봇 재시작
sudo systemctl restart discord-bot
```

---

## 🔧 트러블슈팅

### 문제 1: "ModuleNotFoundError: No module named 'discord'"

```bash
# 해결
cd /home/discord-bot/Akitect
source venv/bin/activate
pip install -r requirements.txt
```

### 문제 2: "DISCORD_TOKEN environment variable not set"

```bash
# .env 파일 확인
cat /home/discord-bot/Akitect/.env

# 파일 재생성
nano /home/discord-bot/Akitect/.env
# DISCORD_TOKEN=your_token_here 추가
```

### 문제 3: "Permission denied" 에러

```bash
# 권한 확인
ls -la /home/discord-bot/Akitect/

# 권한 변경 (필요시)
chmod 755 /home/discord-bot/Akitect
chmod 644 /home/discord-bot/Akitect/.env
```

### 문제 4: 봇이 자동 재시작되지 않음

```bash
# Systemd 서비스 상태 확인
sudo systemctl status discord-bot

# 서비스 로그 확인
sudo journalctl -u discord-bot -n 50

# 서비스 재로드
sudo systemctl daemon-reload
sudo systemctl restart discord-bot
```

### 문제 5: 높은 CPU/메모리 사용

```bash
# 현재 메모리 사용
free -h

# 프로세스별 사용량
ps aux --sort=-%mem | head -10

# 봇 프로세스 확인
ps aux | grep "python main.py"
```

---

## 📈 고급 설정

### 1. 자동 백업

```bash
# 백업 스크립트 생성
cat > ~/backup-bot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/discord-bot/backups"
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/bot-$(date +%Y%m%d-%H%M%S).tar.gz /home/discord-bot/Akitect
echo "✅ Backup completed"
EOF

# 실행 권한
chmod +x ~/backup-bot.sh

# Cron으로 매일 자정에 백업
crontab -e
# 추가: 0 0 * * * /home/backup-bot.sh
```

### 2. 모니터링 (Uptime Robot 연동)

```bash
# 헬스 체크 엔드포인트 (선택사항)
# main.py에 추가할 수 있음

# Uptime Robot (https://uptimerobot.com)에서
# 봇이 살아있는지 주기적으로 체크
```

### 3. 로그 로테이션

```bash
# logrotate 설정
sudo nano /etc/logrotate.d/discord-bot
```

파일 내용:
```
/home/discord-bot/Akitect/bot.log
/home/discord-bot/Akitect/error.log
{
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 debian debian
}
```

---

## 🌐 Google Cloud 비용 절감

### 1. 저렴한 인스턴스 타입

```
권장: e2-micro (항상 무료 한도)
- vCPU: 0.25-1
- 메모리: 1GB
- 비용: 무료 (월 730시간까지)
```

### 2. 자동 종료 설정

**원하는 경우만:**
```
Google Cloud Console
→ VM 인스턴스
→ 인스턴스 선택
→ 수정 → 스케줄 설정
```

### 3. 영구 디스크 최적화

```bash
# 불필요한 파일 삭제
du -sh /home/discord-bot/*
rm -rf /home/discord-bot/Akitect/.pytest_cache
rm -rf /home/discord-bot/Akitect/__pycache__
```

---

## 📝 체크리스트

배포 전 확인사항:

- [ ] VM 인스턴스 생성 및 SSH 접속 가능
- [ ] Python 3.10+ 설치
- [ ] 프로젝트 파일 업로드
- [ ] 가상환경 생성 및 패키지 설치
- [ ] `.env` 파일 생성 및 토큰 설정
- [ ] 로컬에서 테스트 실행 성공
- [ ] Systemd 서비스 파일 생성
- [ ] 서비스 활성화 및 시작
- [ ] 로그 확인 (에러 없음)
- [ ] 디스코드에서 명령어 테스트

---

## 🆘 도움이 필요하면

### 로그 확인 (가장 중요!)

```bash
# 실시간으로 에러 확인
sudo journalctl -u discord-bot -f | grep ERROR

# 또는
tail -f /home/discord-bot/Akitect/bot.log
```

### Google Cloud 지원

```
Google Cloud Console
→ 지원
→ 티켓 생성
```

### Discord 봇 문서

```
https://discordpy.readthedocs.io/
```

---

## 🎉 완료!

이제 Discord 봇이 Google Cloud VM에서 24/7 실행됩니다! 🚀

**다음 단계:**
1. 명령어 테스트
2. 디스코드 서버에서 기능 확인
3. 설정 최적화

**행운을 빕니다!** 🍀

---

**마지막 업데이트**: 2026년 4월 18일
**호스팅**: Google Cloud VM (Ubuntu 22.04 LTS)
**상태**: ✅ 즉시 배포 가능
