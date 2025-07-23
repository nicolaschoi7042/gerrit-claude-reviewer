#!/bin/bash

# 스크립트 실행 중 오류가 발생하면 즉시 중단합니다.
set -e

# 1. 패키지 목록 업데이트 및 curl 설치
echo "Updating package list and installing curl..."
sudo apt-get update
sudo apt-get install -y curl

# 2. nvm (Node Version Manager) 설치
echo "Installing nvm..."
export NVM_DIR="$HOME/.nvm"
if [ -d "$NVM_DIR" ]; then
  echo "nvm is already installed."
else
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

# 현재 셸에서 nvm을 사용하기 위해 환경 변수를 로드합니다.
# .bashrc에 이미 설정되어 있을 수 있으므로, 중복을 피하기 위해 확인합니다.
if ! grep -q 'export NVM_DIR' ~/.bashrc; then
    echo 'export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"' >> ~/.bashrc
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm' >> ~/.bashrc
fi

# nvm 스크립트를 source하여 현재 세션에서 nvm 명령어 사용 가능하게 함
source "$NVM_DIR/nvm.sh"


# 3. Node.js 20.x LTS 버전 설치 및 사용 (Gemini CLI는 Node.js 20+ 필요)
echo "Installing Node.js 20.x LTS..."
nvm install 20
nvm use 20
nvm alias default 20

# Node.js 및 npm 버전 확인
echo "Node.js and npm versions:"
node -v
npm -v

# 4. Gemini CLI 설치
echo "Installing Gemini CLI..."
npm install -g @google/gemini-cli

# API 키 설정
if command -v gemini &> /dev/null; then
    echo "Setting up Gemini API key..."
    echo 'export GEMINI_API_KEY="AIzaSyAa7SpSgILzz1bBIcmcuTeRo4XY11HB4wM"' >> ~/.bashrc
    source ~/.bashrc
fi

echo "Installation complete!"
echo "Gemini CLI is now installed. Version: $(gemini --version)"
echo ""
echo "To get started:"
echo "1. Set up your API key: gemini auth"
echo "2. Or manually set: export GEMINI_API_KEY=your_api_key_here"
echo "3. Start chatting: gemini chat"
echo "4. For help: gemini --help"
echo ""
echo "Please restart your terminal or run 'source ~/.bashrc' to ensure all commands work properly."
