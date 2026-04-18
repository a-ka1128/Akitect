# ⚡ Google Cloud VM 빠른 배포 (3단계)

Google Cloud VM에서 Discord 봇을 **5분 안에** 배포하는 간단한 가이드입니다.

---

## 📋 준비사항

- ✅ Google Cloud VM 인스턴스 (Ubuntu 22.04 LTS)
- ✅ SSH 접속 가능
- ✅ Discord Bot Token

---

## 🚀 배포 (3단계)

### Step 1: VM에 접속

```bash
# Google Cloud Console에서
Compute Engine → VM 인스턴스
→ 인스턴스 선택 → SSH 클릭

# 또는 gcloud CLI
gcloud compute ssh akitect-bot --zone=us-central1-a
```

### Step 2: 프로젝트 다운로드

#### 옵션 A: GitHub에서 (가장 간단)

```bash
cd ~
git clone https://github.com/your-username/Akitect.git
cd Akitect
```

#### 옵션 B: 로컬에서 업로드

```bash
# 로컬 머신에서
scp -r ./Akitect your-account@vm-ip:~/
```

### Step 3: 자동 배포 실행

```bash
cd ~/Akitect

# 권한 설정
chmod +x deploy.sh

# 배포 스크립트 실행
./deploy.sh
```

스크립트가 자동으로:
- ✅ Python 3 설치 확인
- ✅ 가상환경 생성
- ✅ 패키지 설치
- ✅ .env 파일 확인
- ✅ Systemd 서비스 설정
- ✅ 봇 시작

---

## ⚙️ .env 파일 설정

배포 중에 요청하면:

```bash
# VM에서 .env 파일 생성
nano ~/.Akitect/.env
```

내용:
```env
DISCORD_TOKEN=your_token_here
ALLOWED_USER_IDS=343290913172226049
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## 🎯 배포 후 확인

### 봇 실행 확인

```bash
# 상태 확인
sudo systemctl status discord-bot

# 실시간 로그
sudo journalctl -u discord-bot -f
```

성공 메시지:
```
✅ 로그인 성공: Akitect#1234
📌 설정 파일: settings.json
✅ 슬래시 명령어 동기화: 15개
```

### Discord 서버에서 테스트

```
/동기화
→ ✅ 동기화 완료
```

---

## 🔄 관리 명령어

### 상태 확인

```bash
sudo systemctl status discord-bot
```

### 로그 보기

```bash
# 실시간 로그
sudo journalctl -u discord-bot -f

# 최근 50줄
sudo journalctl -u discord-bot -n 50

# 에러만 보기
sudo journalctl -u discord-bot | grep ERROR
```

### 봇 재시작

```bash
sudo systemctl restart discord-bot
```

### 봇 중지

```bash
sudo systemctl stop discord-bot
```

### 봇 시작

```bash
sudo systemctl start discord-bot
```

### 로그 파일 직접 확인

```bash
# 봇 로그
tail -f ~/Akitect/bot.log

# 에러 로그
tail -f ~/Akitect/error.log
```

---

## 🔄 코드 업데이트

### GitHub에서 최신 버전 적용

```bash
cd ~/Akitect

# 최신 코드 다운로드
git pull origin main

# 패키지 업데이트 (변경됐으면)
source venv/bin/activate
pip install -r requirements.txt

# 봇 재시작
sudo systemctl restart discord-bot
```

---

## 🐛 문제 해결

### Q: 봇이 시작되지 않음

```bash
# 1. 로그 확인
sudo journalctl -u discord-bot -n 50

# 2. .env 파일 확인
cat ~/Akitect/.env

# 3. 토큰 유효한지 확인
# Discord Developer Portal 확인

# 4. 재시작
sudo systemctl restart discord-bot
```

### Q: 높은 CPU/메모리 사용

```bash
# 프로세스 확인
ps aux | grep "python main.py"

# 메모리 사용 확인
free -h
```

### Q: 명령어가 작동하지 않음

```bash
# Discord에서 명령어 동기화
/동기화

# 로그에서 에러 확인
sudo journalctl -u discord-bot | grep ERROR
```

---

## 📊 비용 절감

### 항상 무료 한도 사용

```
e2-micro 인스턴스:
- 월 730시간 무료
- vCPU: 0.25-1
- 메모리: 1GB

Discord 봇은 리소스 사용이 적음
→ 완전히 무료로 운영 가능! 🎉
```

---

## ✅ 체크리스트

- [ ] VM 접속 가능
- [ ] 프로젝트 다운로드
- [ ] deploy.sh 실행
- [ ] .env 파일 설정 (필요시)
- [ ] 서비스 시작 확인
- [ ] 로그에서 "로그인 성공" 확인
- [ ] Discord에서 명령어 테스트

---

## 📖 더 자세한 정보

더 자세한 설정은 **GOOGLE_CLOUD_SETUP.md** 참고

---

## 🎉 완료!

축하합니다! Discord 봇이 Google Cloud에서 24/7 실행 중입니다! 🚀

**행운을 빕니다!** 🍀
