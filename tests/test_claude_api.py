#!/usr/bin/env python3
"""
Claude API를 통한 코드 리뷰 테스트
"""

import json
import logging
import subprocess
import sys

from dotenv import load_dotenv

# 현재 디렉토리의 .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_claude_api():
    """Claude API 테스트"""
    logger.info("Claude API 테스트 시작...")

    try:
        # Claude CLI를 통한 간단한 테스트
        test_prompt = "안녕하세요! 이것은 연결 테스트입니다. 간단히 '연결 확인됨'이라고 답해주세요."

        # claude CLI 명령 실행 (전역 설치된 Claude CLI 사용)
        cmd = f"claude --print '{test_prompt}'"
        logger.info(f"실행 명령: {cmd}")

        result = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # JSON 응답 파싱 시도
            try:
                response_data = json.loads(result.stdout)
                if isinstance(response_data, list) and len(response_data) > 0:
                    # 마지막 메시지 찾기
                    for message in reversed(response_data):
                        if message.get("role") == "assistant":
                            response_text = message.get("content", "")
                            logger.info(f"✅ Claude API 응답: {response_text}")
                            return True
                else:
                    logger.info(f"✅ Claude API 응답 (raw): {result.stdout}")
                    return True
            except json.JSONDecodeError:
                # JSON이 아닌 경우 raw 텍스트로 처리
                logger.info(f"✅ Claude API 응답 (text): {result.stdout}")
                return True
        else:
            logger.error(f"❌ Claude CLI 실행 실패: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("❌ Claude API 호출 시간 초과")
        return False
    except Exception as e:
        logger.error(f"❌ Claude API 테스트 실패: {e}")
        return False


def test_code_review_prompt():
    """코드 리뷰용 프롬프트 테스트"""
    logger.info("코드 리뷰 프롬프트 테스트 시작...")

    sample_code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total
"""

    review_prompt = f"""
다음 Python 코드를 리뷰해주세요. 개선점이나 문제점이 있다면 간단히 알려주세요:

```python
{sample_code.strip()}
```

한 줄로 간단한 코멘트만 주세요.
"""

    try:
        cmd = f"claude --print '{review_prompt}'"
        result = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                if isinstance(response_data, list) and len(response_data) > 0:
                    for message in reversed(response_data):
                        if message.get("role") == "assistant":
                            response_text = message.get("content", "")
                            logger.info(f"✅ 코드 리뷰 응답: {response_text}")
                            return True
            except Exception:
                logger.info(f"✅ 코드 리뷰 응답 (raw): {result.stdout}")
                return True
        else:
            logger.error(f"❌ 코드 리뷰 테스트 실패: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"❌ 코드 리뷰 테스트 오류: {e}")
        return False


if __name__ == "__main__":
    logger.info("🔧 Claude API 연결 및 코드 리뷰 테스트")
    logger.info("=" * 50)

    # 기본 API 테스트
    api_test = test_claude_api()

    # 코드 리뷰 테스트
    review_test = test_code_review_prompt()

    logger.info("=" * 50)
    logger.info("테스트 결과:")
    logger.info(f"  Claude API: {'✅ 성공' if api_test else '❌ 실패'}")
    logger.info(f"  코드 리뷰: {'✅ 성공' if review_test else '❌ 실패'}")

    if api_test and review_test:
        logger.info("🎉 모든 테스트 성공! Claude API를 통한 코드 리뷰 준비 완료!")
        sys.exit(0)
    else:
        logger.error("❌ 일부 테스트 실패")
        sys.exit(1)
