#!/usr/bin/env python3
"""
Claude 웹사이트 로그인 테스트
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 현재 디렉토리의 .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# gerrit_claude_reviewer.py에서 ClaudeReviewer 클래스 임포트
try:
    from gerrit_claude_reviewer import ClaudeReviewer
except ImportError as e:
    logger.error(f"ClaudeReviewer 클래스를 임포트할 수 없습니다: {e}")
    sys.exit(1)

def test_claude_login():
    """Claude 로그인 테스트"""
    logger.info("Claude 로그인 테스트 시작...")
    
    # 환경변수 확인
    email = os.getenv("CLAUDE_EMAIL")
    password = os.getenv("CLAUDE_PASSWORD")
    
    if not email or not password:
        logger.error("CLAUDE_EMAIL 또는 CLAUDE_PASSWORD가 설정되지 않았습니다.")
        logger.error("현재 설정:")
        logger.error(f"  CLAUDE_EMAIL: {email}")
        logger.error(f"  CLAUDE_PASSWORD: {'설정됨' if password else '미설정'}")
        return False
    
    logger.info(f"로그인 계정: {email}")
    
    # ClaudeReviewer 인스턴스 생성 및 연결 테스트
    claude = ClaudeReviewer()
    
    try:
        success = claude.test_connection()
        if success:
            logger.info("✅ Claude 로그인 테스트 성공!")
            return True
        else:
            logger.error("❌ Claude 로그인 테스트 실패")
            return False
    except Exception as e:
        logger.error(f"❌ Claude 로그인 테스트 중 오류: {e}")
        return False

if __name__ == "__main__":
    success = test_claude_login()
    sys.exit(0 if success else 1)