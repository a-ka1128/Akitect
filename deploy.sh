#!/bin/bash

# Google Cloud VM에 Discord 봇 배포 자동화 스크립트
# 사용: chmod +x deploy.sh && ./deploy.sh

set -e  # 에러 발생 시 중단

echo "🚀 Discord 봇 배포 시작..."
echo "================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 시스템 업데이트
echo -e "${YELLOW}📦 시스템 업데이트 중...${NC}"
sudo apt update
sudo apt upgrade -y

# 2. Python 확인
echo -e "${YELLOW}🐍 Python 버전 확인...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "현재 Python 버전: $PYTHON_VERSION"

# 3. 필수 패키지 설치
echo -e "${YELLOW}📦 필수 패키지 설치 중...${NC}"
sudo apt install -y python3-venv python3-dev git curl wget nano

# 4. 프로젝트 디렉토리 준비
echo -e "${YELLOW}📁 프로젝트 디렉토리 준비 중...${NC}"
mkdir -p /home/discord-bot
cd /home/discord-bot

# 프로젝트가 없으면 현재 디렉토리 사용
if [ ! -d "Akitect" ]; then
    echo "현재 디렉토리에서 배포합니다"
    PROJECT_DIR=$(pwd)
else
    PROJECT_DIR="/home/discord-bot/Akitect"
fi

cd "$PROJECT_DIR"

# 5. 가상환경 생성
echo -e "${YELLOW}🔧 가상환경 생성 중...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 가상환경 생성 완료"
else
    echo "✅ 기존 가상환경 사용"
fi

# 6. 패키지 설치
echo -e "${YELLOW}📦 패키지 설치 중 (requirements.txt)...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 7. .env 파일 확인
echo -e "${YELLOW}🔑 환경변수 파일 확인...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env 파일이 없습니다!${NC}"
    echo "다음 내용으로 .env 파일을 생성하세요:"
    echo ""
    echo "DISCORD_TOKEN=your_token_here"
    echo "ALLOWED_USER_IDS=343290913172226049"
    echo ""
    read -p ".env 파일을 생성했으면 Enter를 누르세요..."

    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ .env 파일이 여전히 없습니다. 배포를 중단합니다.${NC}"
        exit 1
    fi
fi
echo "✅ .env 파일 확인 완료"

# 8. 봇 테스트 실행 (선택사항)
echo -e "${YELLOW}🧪 봇 간단한 테스트 중...${NC}"
timeout 10 python main.py > /tmp/bot-test.log 2>&1 || true

if grep -q "로그인 성공" /tmp/bot-test.log; then
    echo -e "${GREEN}✅ 봇 테스트 성공!${NC}"
else
    echo -e "${YELLOW}⚠️ 봇 테스트 스킵 (토큰 확인 필요)${NC}"
fi

# 9. Systemd 서비스 설정
echo -e "${YELLOW}⚙️ Systemd 서비스 설정 중...${NC}"

SERVICE_FILE="/etc/systemd/system/discord-bot.service"

# 사용자 확인
CURRENT_USER=$(whoami)

cat > /tmp/discord-bot.service << EOF
[Unit]
Description=Discord Bot (Akitect)
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python main.py

Restart=always
RestartSec=10

StandardOutput=append:$PROJECT_DIR/bot.log
StandardError=append:$PROJECT_DIR/error.log

[Install]
WantedBy=multi-user.target
EOF

# 서비스 파일 복사 (sudo 필요)
echo -e "${YELLOW}Systemd 서비스 파일을 설치합니다 (암호 필요 가능)...${NC}"
sudo cp /tmp/discord-bot.service "$SERVICE_FILE"
sudo systemctl daemon-reload

# 10. 서비스 활성화 및 시작
echo -e "${YELLOW}🚀 서비스 시작 중...${NC}"
sudo systemctl enable discord-bot
sudo systemctl start discord-bot

# 11. 상태 확인
echo ""
echo -e "${YELLOW}📊 서비스 상태 확인 중...${NC}"
sudo systemctl status discord-bot --no-pager

# 12. 로그 확인
echo ""
echo -e "${YELLOW}📋 최근 로그 확인 중...${NC}"
sleep 2
sudo journalctl -u discord-bot -n 20 --no-pager

echo ""
echo "================================"
echo -e "${GREEN}✅ 배포 완료!${NC}"
echo ""
echo "📌 다음 명령어로 관리할 수 있습니다:"
echo "  • 상태 확인: sudo systemctl status discord-bot"
echo "  • 로그 보기: sudo journalctl -u discord-bot -f"
echo "  • 재시작: sudo systemctl restart discord-bot"
echo "  • 중지: sudo systemctl stop discord-bot"
echo ""
echo "🚀 봇이 Google Cloud에서 실행 중입니다!"
