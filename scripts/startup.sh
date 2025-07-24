#!/bin/bash

echo "🚀 Gerrit Claude Reviewer 시작 중..."
echo "======================================"

# 환경변수 확인
echo "📋 환경변수 확인:"
echo "  GERRIT_HOST: $GERRIT_HOST"
echo "  GERRIT_USERNAME: $GERRIT_USERNAME"
echo "  CLAUDE_EMAIL: $CLAUDE_EMAIL"
echo ""

# Claude CLI 존재 확인
if ! command -v claude &> /dev/null; then
    echo "❌ Claude CLI not found"
    exit 1
fi

echo "✅ Claude CLI found: $(which claude)"

# 1. Gerrit SSH 연결 테스트
echo "🔧 Gerrit SSH 연결 테스트..."
python3 -c "
import os
import sys
from gerrit_claude_reviewer import GerritAPI

try:
    host = os.getenv('GERRIT_HOST')
    port = int(os.getenv('GERRIT_PORT', '29418'))
    username = os.getenv('GERRIT_USERNAME')
    ssh_key_path = '/app/.ssh/id_rsa'

    gerrit = GerritAPI(host, port, username, ssh_key_path)
    version_output = gerrit._run_ssh_command('version')
    print(f'✅ Gerrit 연결 성공: {version_output.strip()}')
except Exception as e:
    print(f'❌ Gerrit 연결 실패: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Gerrit 연결 실패로 서비스를 시작할 수 없습니다."
    exit 1
fi

# 2. Claude API 연결 테스트
echo ""
echo "🤖 Claude API 연결 테스트..."
python3 tests/test_claude_api.py

if [ $? -eq 0 ]; then
    echo "✅ Claude API 연결 성공! 서비스를 시작합니다."
    echo ""

    # 서비스 준비 완료 표시 (health check용)
    touch /tmp/service_ready

    echo "🔄 메인 리뷰어 서비스 시작 중..."
    python3 gerrit_claude_reviewer.py
else
    echo "⚠️  Claude API 연결 실패. 인증을 확인해주세요."
    echo ""
    echo "📝 Claude 인증 방법:"
    echo "  1) 컨테이너 접속: docker compose exec gerrit-nicolas.choi bash"
    echo "  2) Claude CLI 로그인: claude"
    echo ""
    echo "🔄 Claude 없이 Gerrit 모니터링만 시작합니다..."

    # 부분 서비스 준비 완료 표시
    touch /tmp/service_ready

    # Claude 없이 Gerrit만 모니터링하는 모드로 실행
    python3 -c "
import time
from gerrit_claude_reviewer import GerritAPI
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info('🔍 Claude 없이 Gerrit 모니터링 모드로 실행 중...')
logger.info('💡 Claude API 인증 후 컨테이너를 재시작하세요.')

# 10분마다 Gerrit 상태 확인
while True:
    try:
        host = os.getenv('GERRIT_HOST')
        port = int(os.getenv('GERRIT_PORT', '29418'))
        username = os.getenv('GERRIT_USERNAME')
        ssh_key_path = '/app/.ssh/id_rsa'

        gerrit = GerritAPI(host, port, username, ssh_key_path)
        changes = gerrit.get_open_changes()
        logger.info(f'📊 Gerrit 상태 확인: {len(changes)}개의 열린 변경사항')

        # 변경사항이 있으면 간단한 정보 출력
        if changes:
            for change in changes[:3]:  # 최대 3개만 표시
                logger.info(f'  📝 Change {change.get(\"number\", \"?\")}: {change.get(\"subject\", \"No subject\")[:50]}...')

    except Exception as e:
        logger.error(f'❌ Gerrit 모니터링 오류: {e}')

    time.sleep(600)  # 10분 대기
    "
fi
