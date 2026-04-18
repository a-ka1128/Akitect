# 🎯 가장 간단한 배포 방법 (권장)

복잡한 설정 없이 **Google Cloud Console의 웹 터미널**에서 바로 배포하는 방법입니다. (5분)

---

## 📋 이 방법의 장점

✅ SSH 키/IP 주소 찾을 필요 없음
✅ 로컬 터미널 설정 필요 없음
✅ 브라우저만 있으면 됨
✅ 가장 간단함

---

## 🚀 5분 안에 배포하기

### Step 1: Google Cloud Console 열기

```
https://console.cloud.google.com
```

### Step 2: Compute Engine 이동

```
왼쪽 메뉴 → Compute Engine → VM 인스턴스
```

### Step 3: 웹 터미널 열기

인스턴스를 선택하면 화면이 보입니다:

```
┌─────────────────────────────────┐
│ 인스턴스: discord-bot           │
│ 상태: 실행 중                   │
│                                 │
│ [SSH 연결▼]  [🔧 수정]  [⋯]   │
│      ↑                          │
│   이 버튼 클릭!                 │
└─────────────────────────────────┘
```

**"SSH 연결" 버튼 클릭** → 화면 아래에 웹 터미널이 열립니다

---

## ⌨️ 웹 터미널에서 명령어 입력

### Step 4: 프로젝트 다운로드

#### 옵션 A: GitHub에서 (가장 추천)

```bash
git clone https://github.com/your-username/Akitect.git
cd Akitect
```

**아직 GitHub에 푸시하지 않았으면:**

로컬에서 먼저 푸시:
```bash
cd ~/Akitect
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/Akitect.git
git push -u origin main
```

#### 옵션 B: Cloud Storage에서

```bash
# Cloud Storage에 파일 업로드한 경우
gsutil -m cp -r gs://your-bucket/Akitect ./
cd Akitect
```

#### 옵션 C: 웹 터미널에서 직접 생성

```bash
# 폴더 생성
mkdir -p ~/Akitect
cd ~/Akitect

# 파일 생성 (nano 에디터 사용)
nano main.py
# 코드 붙여넣기...
```

**가장 간단한 방법은 옵션 A (GitHub)입니다!** ✨

### Step 5: .env 파일 생성

```bash
nano .env
```

다음 내용 입력:

```env
DISCORD_TOKEN=your_token_here
ALLOWED_USER_IDS=343290913172226049
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

### Step 6: 배포 스크립트 실행

```bash
chmod +x deploy.sh
./deploy.sh
```

**스크립트가 모든 것을 자동으로 설정합니다!**

---

## ✅ 배포 확인

### 스크립트가 완료되면

```bash
# 상태 확인
sudo systemctl status discord-bot
```

예상 출력:
```
● discord-bot.service - Discord Bot (Akitect)
     Loaded: loaded
     Active: active (running)
```

### 로그 확인

```bash
# 최근 로그
sudo journalctl -u discord-bot -n 20
```

예상 메시지:
```
✅ 로그인 성공: Akitect#1234
📌 설정 파일: settings.json
✅ 슬래시 명령어 동기화: 15개
```

---

## 🎮 Discord에서 테스트

Discord 서버의 채팅창에서:

```
/동기화
```

응답:
```
✅ 동기화 완료 (15개 명령어)
```

---

## 📝 웹 터미널 팁

### 터미널이 닫혔을 때

```
Google Cloud Console
→ VM 인스턴스 선택
→ "SSH 연결" 버튼 클릭
→ 다시 열림
```

### 복사/붙여넣기

```
명령어 복사: Ctrl+C
웹 터미널에 붙여넣기: Ctrl+V 또는 마우스 우클릭 → 붙여넣기
```

### 화면이 너무 작으면

```
오른쪽 아래 버튼:
전체화면 보기 👉 ⛶ (모니터 아이콘)
```

### 명령어 자동완성

```
Tab 키: 명령어 자동완성
↑/↓: 이전/다음 명령어
```

---

## 🔄 이후 관리

### 로그 확인

```bash
# 실시간으로 보기
sudo journalctl -u discord-bot -f
```

Ctrl+C로 중단

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

---

## 🐛 문제 발생 시

### "git: command not found"

```bash
# Git 설치
sudo apt update
sudo apt install -y git
```

### ".env 파일이 없다" 에러

```bash
cd ~/Akitect
nano .env
# 아래 내용 입력:
# DISCORD_TOKEN=your_token_here
# ALLOWED_USER_IDS=343290913172226049
```

### 봇이 시작되지 않음

```bash
# 로그 확인
sudo journalctl -u discord-bot -n 50

# .env 파일 확인
cat ~/.env
```

---

## 🎯 다음 단계

1. ✅ 배포 완료
2. ✅ Discord에서 명령어 테스트
3. ✅ 설정 최적화 (필요시)

---

## ⏱️ 예상 소요 시간

| 단계 | 시간 |
|------|------|
| GitHub 클론 | 1분 |
| .env 파일 생성 | 1분 |
| deploy.sh 실행 | 3분 |
| 배포 확인 | 1분 |
| **합계** | **약 6분** |

---

## 💡 추가 팁

### 웹 터미널 주의사항

```
⚠️ 주의: 웹 터미널은 연결을 끊어도 VM에서는 계속 실행됩니다
→ 배포 중 창을 닫아도 괜찮습니다
→ 나중에 다시 열어서 상태 확인 가능
```

### 파일 보기

```bash
# 파일 목록 보기
ls -la

# 파일 내용 보기
cat main.py

# 설정 파일 내용
cat ~/.env
```

### 시스템 정보

```bash
# Python 버전 확인
python3 --version

# 디스크 사용량
df -h

# 메모리 사용량
free -h
```

---

## 🎉 완료!

이제 Discord 봇이 Google Cloud에서 24/7 실행됩니다! 🚀

**축하합니다!** 🎊

---

## 📞 더 필요한 정보

- 로컬에서 SCP로 업로드: `HOW_TO_GET_SSH_INFO.md` 참고
- 자세한 설정: `GOOGLE_CLOUD_SETUP.md` 참고
- 전체 개요: `FINAL_SUMMARY.md` 참고

---

**행운을 빕니다!** 🍀
