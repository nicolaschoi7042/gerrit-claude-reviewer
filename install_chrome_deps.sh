#!/bin/bash

echo "🔧 Gerrit Claude Reviewer - Chrome 의존성 설치 스크립트"
echo "======================================================"

# Chrome 브라우저 확인
echo "1. Chrome 브라우저 확인..."
if command -v google-chrome &> /dev/null; then
    echo "✅ Google Chrome이 이미 설치되어 있습니다"
    google-chrome --version
elif command -v chromium-browser &> /dev/null; then
    echo "✅ Chromium이 이미 설치되어 있습니다"
    chromium-browser --version
else
    echo "📦 Chrome 브라우저 설치 중..."

    # Google Chrome 설치
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
    sudo apt install -y google-chrome-stable

    if [ $? -eq 0 ]; then
        echo "✅ Google Chrome 설치 완료"
    else
        echo "❌ Google Chrome 설치 실패, Chromium으로 시도..."
        sudo apt install -y chromium-browser
    fi
fi

# ChromeDriver 확인 및 설치
echo ""
echo "2. ChromeDriver 확인..."
if command -v chromedriver &> /dev/null; then
    echo "✅ ChromeDriver가 이미 설치되어 있습니다"
    chromedriver --version
else
    echo "📦 ChromeDriver 설치 중..."

    # ChromeDriver 설치 (apt 방식)
    sudo apt install -y chromium-chromedriver

    # 만약 apt 설치가 실패하면 직접 다운로드 (새로운 Chrome for Testing API 사용)
    if ! command -v chromedriver &> /dev/null; then
        echo "📦 ChromeDriver 직접 다운로드 중..."

        # Chrome 버전 확인
        CHROME_VERSION=$(google-chrome --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
        echo "Chrome 풀 버전: $CHROME_VERSION"

        # Chrome for Testing API 사용 (Chrome 115+ 버전용)
        echo "Chrome for Testing API에서 ChromeDriver 다운로드 중..."
        DOWNLOAD_URL="https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip"

        echo "다운로드 URL: $DOWNLOAD_URL"
        wget -O /tmp/chromedriver.zip "$DOWNLOAD_URL"

        if [ $? -eq 0 ]; then
            # 압축 해제 및 설치
            unzip /tmp/chromedriver.zip -d /tmp/
            sudo mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/
            sudo chmod +x /usr/local/bin/chromedriver

            # 정리
            rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64
            echo "✅ ChromeDriver 설치 완료"
        else
            echo "❌ ChromeDriver 다운로드 실패. 호환되는 버전을 찾을 수 없습니다."
            echo "💡 대안: webdriver-manager 사용을 권장합니다."
        fi
    fi
fi

# Python 의존성 설치
echo ""
echo "3. Python 의존성 확인..."
python3 -c "import selenium" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Selenium이 이미 설치되어 있습니다"
else
    echo "📦 Python Selenium 설치 중..."
    pip3 install selenium webdriver-manager
fi

# 추가 시스템 의존성
echo ""
echo "4. 추가 시스템 의존성 설치..."
sudo apt install -y xvfb  # 헤드리스 디스플레이용

# 설치 확인
echo ""
echo "5. 설치 확인..."
echo "===================="

# Chrome 확인
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome: $(google-chrome --version)"
elif command -v chromium-browser &> /dev/null; then
    echo "✅ Chromium: $(chromium-browser --version)"
else
    echo "❌ Chrome/Chromium이 설치되지 않았습니다"
fi

# ChromeDriver 확인
if command -v chromedriver &> /dev/null; then
    echo "✅ ChromeDriver: $(chromedriver --version)"
else
    echo "❌ ChromeDriver가 설치되지 않았습니다"
fi

# Python 의존성 확인
python3 -c "import selenium; print('✅ Selenium:', selenium.__version__)" 2>/dev/null || echo "❌ Selenium이 설치되지 않았습니다"

echo ""
echo "🎉 설치 완료! 이제 'python3 test_claude_login.py'로 테스트할 수 있습니다."
