#!/usr/bin/env python3
"""
Claude 웹사이트 간단 연결 테스트 (Selenium 없이)
"""

import os
import sys
import logging
import requests
from dotenv import load_dotenv

# 현재 디렉토리의 .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_claude_website():
    """Claude 웹사이트 연결 테스트"""
    logger.info("Claude 웹사이트 간단 연결 테스트 시작...")
    
    # 환경변수 확인
    claude_url = os.getenv("CLAUDE_WEB_URL", "https://claude.ai")
    email = os.getenv("CLAUDE_EMAIL")
    password = os.getenv("CLAUDE_PASSWORD")
    
    logger.info(f"Claude URL: {claude_url}")
    logger.info(f"로그인 계정: {email}")
    logger.info(f"비밀번호 설정: {'✓' if password else '✗'}")
    
    try:
        # 브라우저 User-Agent 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # HTTP 연결 테스트
        response = requests.get(claude_url, timeout=10, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"✅ Claude 웹사이트 연결 성공! (HTTP {response.status_code})")
            logger.info(f"응답 크기: {len(response.content)} bytes")
            
            # 로그인 페이지 존재 확인
            if "login" in response.text.lower() or "sign" in response.text.lower():
                logger.info("✅ 로그인 페이지 요소 발견")
            else:
                logger.warning("⚠️ 로그인 페이지 요소를 찾을 수 없음")
                
            return True
        else:
            logger.error(f"❌ Claude 웹사이트 연결 실패: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ Claude 웹사이트 연결 타임아웃")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Claude 웹사이트 연결 실패: {e}")
        return False

def test_dependencies():
    """필요한 의존성 테스트"""
    logger.info("의존성 테스트 시작...")
    
    try:
        import selenium
        logger.info(f"✅ Selenium 버전: {selenium.__version__}")
    except ImportError:
        logger.error("❌ Selenium이 설치되지 않음")
        return False
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        logger.info("✅ Selenium WebDriver 모듈 로드 성공")
    except ImportError as e:
        logger.error(f"❌ Selenium WebDriver 모듈 로드 실패: {e}")
        return False
    
    # ChromeDriver 확인
    chrome_driver_path = os.getenv("CHROME_DRIVER_PATH", "/usr/bin/chromedriver")
    if os.path.exists(chrome_driver_path):
        logger.info(f"✅ ChromeDriver 발견: {chrome_driver_path}")
    else:
        logger.warning(f"⚠️ ChromeDriver를 찾을 수 없음: {chrome_driver_path}")
    
    return True

if __name__ == "__main__":
    logger.info("=== Claude 로그인 환경 테스트 ===")
    
    # 의존성 테스트
    if not test_dependencies():
        sys.exit(1)
    
    # 웹사이트 연결 테스트
    success = test_claude_website()
    
    if success:
        logger.info("🎉 기본 연결 테스트 성공! Selenium을 이용한 실제 로그인은 Chrome 브라우저가 필요합니다.")
    else:
        logger.error("💥 연결 테스트 실패")
    
    sys.exit(0 if success else 1)