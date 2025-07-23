#!/usr/bin/env python3
"""
통합 리뷰 시스템 테스트
"""

import logging
import os
import sys

from dotenv import load_dotenv

# 현재 디렉토리의 .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    from gerrit_claude_reviewer import ClaudeReviewer, GerritAPI
except ImportError as e:
    logger.error(f"모듈 임포트 실패: {e}")
    sys.exit(1)


def test_gerrit_connection():
    """Gerrit 연결 테스트"""
    logger.info("Gerrit 연결 테스트 시작...")

    try:
        host = os.getenv("GERRIT_HOST")
        port = int(os.getenv("GERRIT_PORT", "29418"))
        username = os.getenv("GERRIT_USERNAME")
        ssh_key_path = os.getenv("SSH_KEY_PATH", "/app/.ssh/id_rsa")

        gerrit = GerritAPI(host, port, username, ssh_key_path)
        changes = gerrit.get_open_changes()

        logger.info(f"✅ Gerrit 연결 성공: {len(changes)}개의 열린 변경사항")
        return True, changes[:3]  # 처음 3개만 반환

    except Exception as e:
        logger.error(f"❌ Gerrit 연결 실패: {e}")
        return False, []


def test_claude_connection():
    """Claude API 연결 테스트"""
    logger.info("Claude API 연결 테스트 시작...")

    try:
        claude = ClaudeReviewer()
        success = claude.test_connection()

        if success:
            logger.info("✅ Claude API 연결 성공")
            return True
        else:
            logger.error("❌ Claude API 연결 실패")
            return False

    except Exception as e:
        logger.error(f"❌ Claude API 테스트 실패: {e}")
        return False


def test_code_review():
    """코드 리뷰 기능 테스트"""
    logger.info("코드 리뷰 기능 테스트 시작...")

    try:
        claude = ClaudeReviewer()

        # 샘플 코드 변경사항
        sample_diff = """@@ -1,5 +1,8 @@
 def calculate_total(items):
-    total = 0
-    for item in items:
-        total += item.price
-    return total
+    if not items:
+        return 0
+
+    total = sum(item.price for item in items)
+    # TODO: Add tax calculation
+    return total"""

        review_result = claude.review_code_change("src/calculator.py", sample_diff)

        logger.info("✅ 코드 리뷰 성공:")
        logger.info(f"리뷰 결과: {review_result[:200]}...")
        return True

    except Exception as e:
        logger.error(f"❌ 코드 리뷰 테스트 실패: {e}")
        return False


def test_full_integration():
    """전체 통합 테스트"""
    logger.info("전체 통합 테스트 시작...")

    try:
        # Gerrit에서 실제 변경사항 가져오기
        host = os.getenv("GERRIT_HOST")
        port = int(os.getenv("GERRIT_PORT", "29418"))
        username = os.getenv("GERRIT_USERNAME")
        ssh_key_path = os.getenv("SSH_KEY_PATH", "/app/.ssh/id_rsa")

        gerrit = GerritAPI(host, port, username, ssh_key_path)
        claude = ClaudeReviewer()

        changes = gerrit.get_open_changes()

        if not changes:
            logger.info("리뷰할 변경사항이 없습니다")
            return True

        # 첫 번째 변경사항 리뷰 시도
        change = changes[0]
        logger.info(f"변경사항 리뷰 시도: {change.subject[:50]}...")

        files = gerrit.get_change_files(change.number, change.current_revision)

        if not files:
            logger.info("리뷰할 파일이 없습니다")
            return True

        # 첫 번째 파일 리뷰
        file_path = list(files.keys())[0]
        diff_content = gerrit.get_file_diff(change.number, change.current_revision, file_path)

        if diff_content:
            review_result = claude.review_code_change(file_path, diff_content)
            logger.info("✅ 통합 테스트 성공!")
            logger.info(f"파일: {file_path}")
            logger.info(f"리뷰: {review_result[:200]}...")
            return True
        else:
            logger.info("diff 내용을 가져올 수 없습니다")
            return True

    except Exception as e:
        logger.error(f"❌ 통합 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    logger.info("🔧 Gerrit Claude 리뷰어 통합 테스트")
    logger.info("=" * 60)

    # 개별 테스트 실행
    gerrit_ok, sample_changes = test_gerrit_connection()
    claude_ok = test_claude_connection()
    review_ok = test_code_review()

    logger.info("=" * 60)
    logger.info("개별 테스트 결과:")
    logger.info(f"  Gerrit 연결: {'✅ 성공' if gerrit_ok else '❌ 실패'}")
    logger.info(f"  Claude API: {'✅ 성공' if claude_ok else '❌ 실패'}")
    logger.info(f"  코드 리뷰: {'✅ 성공' if review_ok else '❌ 실패'}")

    if gerrit_ok and claude_ok and review_ok:
        logger.info("=" * 60)
        integration_ok = test_full_integration()
        logger.info(f"  전체 통합: {'✅ 성공' if integration_ok else '❌ 실패'}")

        if integration_ok:
            logger.info("🎉 모든 테스트 성공! 리뷰어 시스템 준비 완료!")
            sys.exit(0)
        else:
            logger.error("❌ 통합 테스트 실패")
            sys.exit(1)
    else:
        logger.error("❌ 기본 테스트 실패")
        sys.exit(1)
