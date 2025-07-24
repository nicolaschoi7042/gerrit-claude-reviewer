#!/bin/bash

# 스크립트 실행 중 오류가 발생하면 즉시 중단합니다.
set -e

echo "🔧 Gerrit Claude Reviewer 설치 스크립트"
echo "======================================"

# 1. 패키지 목록 업데이트 및 기본 패키지 설치
echo "📦 Updating package list and installing dependencies..."
sudo apt-get update
sudo apt-get install -y curl git python3-pip python3-venv

# 2. nvm (Node Version Manager) 설치
echo "🚀 Installing nvm..."
export NVM_DIR="$HOME/.nvm"
if [ -d "$NVM_DIR" ]; then
  echo "✅ nvm is already installed."
else
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

# 현재 셸에서 nvm을 사용하기 위해 환경 변수를 로드합니다.
if ! grep -q 'export NVM_DIR' ~/.bashrc; then
    echo 'export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"' >> ~/.bashrc
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm' >> ~/.bashrc
fi

# nvm 스크립트를 source하여 현재 세션에서 nvm 명령어 사용 가능하게 함
source "$NVM_DIR/nvm.sh"

# 3. Node.js 20.x LTS 버전 설치 및 사용 (Claude CLI는 Node.js 18+ 필요)
echo "🟢 Installing Node.js 20.x LTS..."
nvm install 20
nvm use 20
nvm alias default 20

# Node.js 및 npm 버전 확인
echo "📋 Node.js and npm versions:"
node -v
npm -v

# 4. Claude CLI 설치
echo "🤖 Installing Claude CLI..."
npm install -g @anthropic-ai/claude-code

# 5. Python 의존성 설치
echo "🐍 Installing Python dependencies..."
if [ -f "../requirements.txt" ]; then
    pip3 install -r ../requirements.txt
else
    echo "⚠️  requirements.txt not found, skipping Python dependencies"
fi

echo ""
echo "✅ Installation complete!"
if command -v claude &> /dev/null; then
    echo "🎉 Claude CLI is now installed."
else
    echo "❌ Claude CLI installation failed"
    exit 1
fi

echo ""
echo "🚀 To get started:"
echo "1. Set up your .env file with Gerrit credentials"
echo "2. Authenticate with Claude: claude"
echo "3. Start the service: ./scripts/startup.sh"
echo "4. For help: claude --help"
echo ""
echo "Please restart your terminal or run 'source ~/.bashrc' to ensure all commands work properly."
