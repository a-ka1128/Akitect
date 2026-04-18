# 🔍 SSH 접속 정보 찾기

Google Cloud VM의 SSH 접속 정보를 찾는 방법입니다.

---

## 📌 SSH 접속 정보 구성

```
your-account@vm-ip
```

이것은 두 부분으로 나뉩니다:

- **your-account**: 당신의 Google 계정 이메일 또는 사용자명
- **vm-ip**: Google Cloud VM의 공개 IP 주소

---

## 방법 1: Google Cloud Console에서 찾기 (추천) ⭐

### Step 1: Google Cloud Console 열기

```
https://console.cloud.google.com
```

### Step 2: Compute Engine 접속

```
왼쪽 메뉴
→ Compute Engine
→ VM 인스턴스
```

### Step 3: 인스턴스 선택

생성한 VM 인스턴스를 클릭하면 상세 정보가 보입니다.

예시 화면:

```
인스턴스 세부정보
├─ 이름: discord-bot
├─ 상태: 실행 중
├─ 외부 IP: 34.123.45.67  👈 이것이 vm-ip!
└─ 내부 IP: 10.128.0.2
```

**외부 IP**: `34.123.45.67` (예시)

### Step 4: 사용자명 확인

콘솔 오른쪽 위의 프로필을 클릭하면 이메일이 보입니다.

예시:
```
your-email@gmail.com  👈 이것이 your-account!
```

---

## 방법 2: 터미널에서 찾기

### Google Cloud SDK 설치 확인

```bash
gcloud --version
```

설치되지 않았으면: https://cloud.google.com/sdk/docs/install

### SSH 접속 정보 출력

```bash
gcloud compute instances describe discord-bot --zone=us-central1-a --format='value(networkInterfaces[0].accessConfigs[0].natIP)'
```

출력:
```
34.123.45.67
```

### 사용자명 확인

```bash
gcloud config get-value account
```

출력:
```
your-email@gmail.com
```

---

## 예시

### 가정: 다음 정보를 확인했습니다

```
Google 계정: john@gmail.com
VM 외부 IP: 34.123.45.67
```

### SSH 명령어

```bash
# 정보 대입
scp -r ./Akitect john@34.123.45.67:~/
```

**`john` 부분은 이메일 앞부분입니다:**
```
john@gmail.com → john
alice@company.com → alice
```

---

## ⚙️ SSH 설정 (선택사항)

매번 IP를 입력하는 게 번거로우면, SSH config 파일을 수정할 수 있습니다.

### Step 1: SSH config 파일 편집

```bash
# Mac/Linux
nano ~/.ssh/config

# Windows (Git Bash)
nano ~/.ssh/config
```

### Step 2: 내용 추가

```
Host discord-bot
    HostName 34.123.45.67
    User john
    IdentityFile ~/.ssh/google_compute_engine
```

### Step 3: 저장

```
Ctrl+O → Enter → Ctrl+X
```

### Step 4: 간단하게 접속

이제 다음처럼 간단하게 접속 가능:

```bash
# 파일 업로드
scp -r ./Akitect discord-bot:~/

# SSH 접속
ssh discord-bot
```

---

## 🔑 SSH 키 설정

### Google Cloud의 기본 SSH 키

Google Cloud Console의 "SSH" 버튼을 클릭하면:
- 자동으로 SSH 키 생성
- 브라우저 기반 터미널 열림
- 별도 설정 불필요 ✅

### 수동 SSH 키 설정 (선택)

더 자세한 제어가 필요하면:

```bash
# SSH 키 생성
ssh-keygen -t rsa -N "" -f ~/.ssh/gce-key

# Google Cloud에 공개키 등록
gcloud compute os-login ssh-keys add --key-file=~/.ssh/gce-key.pub

# 접속 테스트
ssh -i ~/.ssh/gce-key john@34.123.45.67
```

---

## 🧪 접속 테스트

### 1. Console SSH로 테스트 (가장 쉬움)

Google Cloud Console에서 "SSH" 버튼 클릭:

```
Google Cloud Console
→ VM 인스턴스 선택
→ 화면 오른쪽 위 "SSH" 버튼 클릭
→ 브라우저에서 터미널 열림
```

### 2. 로컬 터미널에서 테스트

```bash
# 파일 업로드 테스트
scp test.txt john@34.123.45.67:~/

# SSH 접속 테스트
ssh john@34.123.45.67
# 명령어 입력 가능한지 확인
exit
```

---

## 📝 정보 저장

당신의 정보를 여기에 기록해두세요:

```
Google 계정: ____________________
VM 이름: ____________________
외부 IP: ____________________
SSH 명령어: scp -r ./Akitect ____@____:~/
```

⚠️ **주의**: 이 정보는 안전하게 보관하세요!

---

## 🚀 이제 배포 가능!

```bash
# 정보를 대입한 후 실행
scp -r ./Akitect your-account@vm-ip:~/

# 예시
scp -r ./Akitect john@34.123.45.67:~/
```

---

## 🆘 문제 해결

### Q: "Permission denied" 에러

```bash
# 원인: SSH 키 권한 문제
chmod 600 ~/.ssh/gce-key

# 다시 시도
scp -i ~/.ssh/gce-key -r ./Akitect john@34.123.45.67:~/
```

### Q: "Host not reachable" 에러

```bash
# IP 주소 다시 확인
gcloud compute instances list

# 방화벽 설정 확인
gcloud compute firewall-rules list

# VM이 실행 중인지 확인
gcloud compute instances describe discord-bot --zone=us-central1-a
```

### Q: Console SSH는 되는데 로컬에서 안 됨

```bash
# 로컬 SSH 키 설정 필요
# 또는 Console SSH로 파일 업로드 (아래 참고)
```

---

## 💡 다른 방법: Console SSH로 업로드

Console의 웹 터미널에서 직접 업로드 가능:

```bash
# 1. Console에서 SSH 클릭 (웹 터미널 열림)
# 2. 파일 다운로드
git clone https://github.com/your-username/Akitect.git
# 또는
wget https://your-storage.com/Akitect.zip
unzip Akitect.zip

# 3. 배포 시작
cd Akitect
chmod +x deploy.sh
./deploy.sh
```

---

## ✅ 정리

### 가장 간단한 방법

```
1. Google Cloud Console 열기
2. VM 인스턴스 선택
3. "SSH" 버튼 클릭 (웹 터미널)
4. 터미널에서 git clone 또는 wget으로 파일 다운로드
5. deploy.sh 실행
```

**이 방법이 가장 간단합니다!** ✨

---

**더 질문 있으면 물어봐주세요!** 🙏
