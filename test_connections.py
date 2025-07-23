#!/usr/bin/env python3
"""
연결 테스트 스크립트
Gerrit SSH와 Claude API 연결을 독립적으로 테스트합니다.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from gerrit_claude_reviewer import GerritAPI, ClaudeReviewer

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gerrit_ssh():
    """Gerrit SSH 연결 테스트"""
    print("\n=== Gerrit SSH 연결 테스트 ===")
    
    # .env 파일에서 설정 읽기
    host = os.getenv("GERRIT_HOST", "your-gerrit-server.com")
    port = int(os.getenv("GERRIT_PORT", "29418"))
    username = os.getenv("GERRIT_USERNAME", "claude-reviewer")
    ssh_key_path = os.path.expanduser(os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa"))
    
    print(f"호스트: {host}")
    print(f"포트: {port}")
    print(f"사용자: {username}")
    print(f"SSH 키: {ssh_key_path}")
    
    try:
        gerrit = GerritAPI(host, port, username, ssh_key_path)
        
        # 버전 확인
        version_output = gerrit._run_ssh_command('version')
        print(f"✅ Gerrit 버전: {version_output.strip()}")
        
        # 간단한 쿼리 테스트
        query_output = gerrit._run_ssh_command('query --format=JSON status:open limit:1')
        if query_output.strip():
            print("✅ 쿼리 테스트 성공")
        else:
            print("⚠️  쿼리 결과가 비어있습니다")
        
        return True
        
    except Exception as e:
        print(f"❌ Gerrit SSH 연결 실패: {e}")
        return False

def test_claude_api():
    """Claude API 연결 테스트"""
    print("\n=== Claude API 연결 테스트 ===")
    
    api_key = os.getenv("CLAUDE_API_KEY", "your-claude-api-key")
    
    if api_key == "your-claude-api-key":
        print("❌ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다")
        return False
    
    print(f"API 키: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        claude = ClaudeReviewer()  # 자동으로 .env에서 읽어옴
        
        if claude.test_connection():
            print("✅ Claude API 연결 성공")
            return True
        else:
            print("❌ Claude API 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ Claude API 테스트 실패: {e}")
        return False

def main():
    print("🔧 Gerrit Claude 리뷰어 연결 테스트")
    print("=" * 50)
    
    # 환경변수 확인
    print("\n=== 환경변수 확인 ===")
    env_vars = ["GERRIT_HOST", "GERRIT_PORT", "GERRIT_USERNAME", "SSH_KEY_PATH", "CLAUDE_API_KEY"]
    
    for var in env_vars:
        value = os.getenv(var, "설정되지 않음")
        if var == "CLAUDE_API_KEY" and value != "설정되지 않음":
            value = f"{value[:10]}...{value[-4:]}"
        print(f"{var}: {value}")
    
    # 연결 테스트 실행
    gerrit_ok = test_gerrit_ssh()
    claude_ok = test_claude_api()
    
    print("\n=== 테스트 결과 ===")
    print(f"Gerrit SSH: {'✅ OK' if gerrit_ok else '❌ FAIL'}")
    print(f"Claude API: {'✅ OK' if claude_ok else '❌ FAIL'}")
    
    if gerrit_ok and claude_ok:
        print("\n🎉 모든 연결 테스트 성공! 리뷰어를 시작할 수 있습니다.")
        return 0
    else:
        print("\n⚠️  일부 연결에 문제가 있습니다. 설정을 확인해주세요.")
        return 1

if __name__ == "__main__":
    sys.exit(main())