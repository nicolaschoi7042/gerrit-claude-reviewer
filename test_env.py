#!/usr/bin/env python3
"""
.env 파일 로딩 테스트
"""

try:
    from dotenv import load_dotenv
    import os
    
    print("=== .env 파일 로딩 테스트 ===")
    
    # .env 파일 로드
    load_dotenv()
    
    # .env에서 로드된 환경변수 확인
    env_vars = {
        'GERRIT_HOST': os.getenv('GERRIT_HOST'),
        'GERRIT_PORT': os.getenv('GERRIT_PORT'),
        'GERRIT_USERNAME': os.getenv('GERRIT_USERNAME'),
        'SSH_KEY_PATH': os.getenv('SSH_KEY_PATH'),
        'CLAUDE_API_KEY': os.getenv('CLAUDE_API_KEY')
    }
    
    for key, value in env_vars.items():
        if key == 'CLAUDE_API_KEY' and value and value != 'your-claude-api-key':
            print(f"{key}: {'*' * 10}{value[-4:]}")
        else:
            print(f"{key}: {value}")
    
    print("\n✅ .env 파일이 성공적으로 로드되었습니다!")
    
except ImportError:
    print("❌ python-dotenv 모듈이 설치되지 않았습니다.")
    print("pip install python-dotenv 를 실행해주세요.")
except Exception as e:
    print(f"❌ 오류 발생: {e}")