#!/usr/bin/env python3
"""
Gerrit Claude 리뷰어 - 스케줄러 기반
"""

import json
import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List

import schedule
from dotenv import load_dotenv

# Selenium imports removed - using Claude CLI API instead

# .env 파일 로드 (시스템 환경변수에서 경로 읽기)
default_env_file = os.getenv("DEFAULT_ENV_FILE")
if default_env_file is None:
    # DEFAULT_ENV_FILE도 설정되지 않은 경우 기본 동작
    load_dotenv()
else:
    load_dotenv(os.getenv("ENV_FILE", default_env_file))


# 로깅 설정
log_file = os.getenv("LOG_FILE", "gerrit_claude_reviewer.log")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class Change:
    change_id: str
    number: str
    subject: str
    owner: Dict
    status: str
    current_revision: str
    updated: str


class GerritAPI:
    def __init__(self, host: str, port: int, username: str, ssh_key_path: str):
        self.host = host
        self.port = port
        self.username = username
        self.ssh_key_path = ssh_key_path

        # SSH 키 파일 확인
        if not os.path.exists(ssh_key_path):
            raise FileNotFoundError(f"SSH key not found: {ssh_key_path}")

    def _run_ssh_command(self, gerrit_command: str) -> str:
        """SSH를 통해 Gerrit 명령 실행"""
        ssh_command = [
            "ssh",
            "-p",
            str(self.port),
            "-i",
            self.ssh_key_path,
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            f"{self.username}@{self.host}",
            "gerrit",
            gerrit_command,
        ]

        try:
            result = subprocess.run(ssh_command, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"SSH command failed: {e.stderr}")
            raise

    def get_open_changes(self, query: str = "status:open") -> List[Change]:
        """열려있는 변경사항 목록 가져오기"""
        # query 명령어로 변경사항 조회
        command = f"query --format=JSON --current-patch-set {shlex.quote(query)}"

        try:
            output = self._run_ssh_command(command)

            changes = []
            for line in output.strip().split("\n"):
                if not line:
                    continue

                data = json.loads(line)

                # 마지막 라인은 통계 정보이므로 제외
                if "type" in data and data["type"] == "stats":
                    continue

                if "number" in data:
                    changes.append(
                        Change(
                            change_id=data.get("id", ""),
                            number=str(data["number"]),
                            subject=data.get("subject", ""),
                            owner=data.get("owner", {}),
                            status=data.get("status", ""),
                            current_revision=data.get("currentPatchSet", {}).get("revision", ""),
                            updated=data.get("lastUpdated", ""),
                        )
                    )

            return changes

        except Exception as e:
            logger.error(f"Gerrit query failed: {e}")
            return []

    def get_change_files(self, change_number: str, patchset_number: str = None) -> Dict:
        """특정 변경사항의 파일 목록 가져오기"""
        if patchset_number:
            command = f"query --files --patch-sets change:{change_number} --format=JSON"
        else:
            command = f"query --files --current-patch-set change:{change_number} --format=JSON"

        try:
            output = self._run_ssh_command(command)

            for line in output.strip().split("\n"):
                if not line:
                    continue

                data = json.loads(line)

                # 통계 정보 제외
                if "type" in data and data["type"] == "stats":
                    continue

                # 파일 정보 추출
                if "currentPatchSet" in data:
                    files = data["currentPatchSet"].get("files", [])
                    file_dict = {}
                    for file_info in files:
                        if file_info["file"] != "/COMMIT_MSG":
                            file_dict[file_info["file"]] = {
                                "lines_inserted": file_info.get("insertions", 0),
                                "lines_deleted": file_info.get("deletions", 0),
                                "type": file_info.get("type", "MODIFIED"),
                            }
                    return file_dict

            return {}

        except Exception as e:
            logger.error(f"Failed to get file list: {e}")
            return {}

    def get_file_diff(self, change_number: str, patchset_number: str, file_path: str) -> str:
        """파일의 변경 정보 가져오기 - 향상된 요약 제공"""
        try:
            # 파일 변경 요약 정보를 더 상세하게 가져오기
            return self._get_enhanced_file_summary(change_number, file_path)

        except Exception as e:
            logger.error(f"Failed to get file diff: {e}")
            return self._get_file_summary(change_number, file_path)

    def _get_current_revision(self, change_number: str) -> str:
        """현재 패치셋의 revision 가져오기"""
        try:
            command = f"query --current-patch-set change:{change_number} --format=JSON"
            output = self._run_ssh_command(command)

            for line in output.strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                if "type" in data and data["type"] == "stats":
                    continue

                if "currentPatchSet" in data:
                    return data["currentPatchSet"].get("revision", "")

            return ""
        except Exception as e:
            logger.debug(f"Failed to get current revision: {e}")
            return ""

    def _get_parent_revision(self, change_number: str) -> str:
        """부모 패치셋의 revision 가져오기"""
        try:
            command = f"query --current-patch-set change:{change_number} --format=JSON"
            output = self._run_ssh_command(command)

            for line in output.strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                if "type" in data and data["type"] == "stats":
                    continue

                if "currentPatchSet" in data:
                    parents = data["currentPatchSet"].get("parents", [])
                    if parents:
                        return parents[0]  # 첫 번째 부모 사용

            return ""
        except Exception as e:
            logger.debug(f"Failed to get parent revision: {e}")
            return ""

    def _get_enhanced_file_summary(self, change_number: str, file_path: str) -> str:
        """향상된 파일 변경 요약 정보 가져오기"""
        try:
            command = f"query --files --current-patch-set change:{change_number} --format=JSON"
            output = self._run_ssh_command(command)

            # 프로젝트 정보와 커밋 메시지도 가져오기
            detail_command = f"query change:{change_number} --format=JSON"
            detail_output = self._run_ssh_command(detail_command)

            project_name = ""
            commit_message = ""

            # 상세 정보 파싱
            for line in detail_output.strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                if "type" in data and data["type"] == "stats":
                    continue

                project_name = data.get("project", "")
                commit_message = data.get("subject", "")
                break

            # 파일 정보 파싱
            for line in output.strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                if "type" in data and data["type"] == "stats":
                    continue

                if "currentPatchSet" in data:
                    files = data["currentPatchSet"].get("files", [])
                    for file_info in files:
                        if file_info["file"] == file_path:
                            file_type = file_info.get("type", "MODIFIED")
                            insertions = file_info.get("insertions", 0)
                            deletions = file_info.get("deletions", 0)

                            # 파일 확장자로 파일 타입 추정
                            file_ext = file_path.split(".")[-1].lower() if "." in file_path else ""

                            # 더 상세한 diff 정보 구성
                            diff_content = f"""=== 파일 변경 분석 ===
프로젝트: {project_name}
커밋 제목: {commit_message}

파일: {file_path}
파일 타입: {file_ext.upper() if file_ext else 'Unknown'} 파일
변경 타입: {file_type}
추가된 라인: {insertions}줄
삭제된 라인: {abs(deletions)}줄
순 변경: {insertions + deletions}줄

=== 분석 가능한 내용 ===
1. 파일 경로로 보아 {'웹소켓 관련' if 'websocket' in file_path or 'ws_' in file_path
   else 'API 관련' if 'api' in file_path or 'connector' in file_path
   else '설정' if any(x in file_path for x in ['.yaml', '.json', '.cfg', '.ini'])
   else '스크립트' if any(x in file_path for x in ['.sh', '.bat', '.py'])
   else '소스코드'} 파일입니다.

2. 변경 규모: {'소규모' if insertions + abs(deletions) < 20
   else '중간 규모' if insertions + abs(deletions) < 100
   else '대규모'} 변경 ({insertions + abs(deletions)}줄)

3. 변경 패턴: {'주로 추가' if insertions > abs(deletions) * 2
   else '주로 삭제' if abs(deletions) > insertions * 2
   else '추가/삭제 균형'}

=== 리뷰 권장사항 ===
• 파일 타입과 변경 규모를 고려한 검토 필요
• {commit_message} 관련 변경사항 검증
• 테스트 케이스 확인 권장"""

                            return diff_content

            return ""

        except Exception as e:
            logger.error(f"Failed to get enhanced file summary: {e}")
            return self._get_file_summary(change_number, file_path)

    def _get_file_summary(self, change_number: str, file_path: str) -> str:
        """파일 변경 요약 정보 가져오기 (fallback)"""
        try:
            command = f"query --files --current-patch-set change:{change_number} --format=JSON"
            output = self._run_ssh_command(command)

            for line in output.strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                if "type" in data and data["type"] == "stats":
                    continue

                if "currentPatchSet" in data:
                    files = data["currentPatchSet"].get("files", [])
                    for file_info in files:
                        if file_info["file"] == file_path:
                            file_type = file_info.get("type", "MODIFIED")
                            insertions = file_info.get("insertions", 0)
                            deletions = file_info.get("deletions", 0)

                            return f"""--- a/{file_path}
+++ b/{file_path}
@@ File Change Summary @@
File: {file_path}
Change Type: {file_type}
Lines Added: {insertions}
Lines Removed: {deletions}
Total Changes: {insertions + deletions} lines

Note: Detailed diff content not available.
Please review based on file path, change type, and modification statistics."""

            return ""

        except Exception as e:
            logger.error(f"Failed to get file summary: {e}")
            return ""

    def _extract_file_diff(self, patch_content: str, file_path: str) -> str:
        """전체 패치에서 특정 파일의 diff 추출"""
        lines = patch_content.split("\n")
        file_diff = []
        in_target_file = False

        for i, line in enumerate(lines):
            if line.startswith("diff --git"):
                if f"b/{file_path}" in line:
                    in_target_file = True
                else:
                    if in_target_file:
                        break
                    in_target_file = False

            if in_target_file:
                file_diff.append(line)

        return "\n".join(file_diff)

    def get_file_content(self, change_number: str, file_path: str) -> str:
        """현재 패치셋의 전체 파일 내용 가져오기 - REST API 사용"""
        try:
            import base64

            import requests

            # Gerrit REST API로 파일 내용 가져오기
            escaped_path = file_path.replace("/", "%2F")
            gerrit_url = f"http://{self.host}/a/changes/{change_number}/revisions/current/files/{escaped_path}/content"

            # SSH 키 기반 인증은 REST API에서 사용할 수 없으므로 기본 인증 시도
            response = requests.get(gerrit_url, timeout=10)

            if response.status_code == 200:
                # Base64 디코딩
                content = base64.b64decode(response.text).decode("utf-8")
                return content
            else:
                logger.debug(f"REST API failed with status {response.status_code}")
                return ""

        except Exception as e:
            logger.debug(f"Failed to get file content for {file_path}: {e}")
            return ""

    def post_review(self, change_number: str, patchset_number: str, message: str, score: int = 0):
        """리뷰 코멘트 작성"""
        # 메시지에서 특수 문자 이스케이프
        escaped_message = shlex.quote(message)

        # review 명령어 구성
        command = f"review --message {escaped_message}"

        # Code-Review 점수 추가 (있는 경우)
        if score != 0:
            command += f" --code-review {score}"

        # 변경사항 지정
        command += f" {change_number},{patchset_number}"

        try:
            self._run_ssh_command(command)
            logger.info(f"리뷰 코멘트 작성 완료: {change_number}")
            return True

        except Exception as e:
            logger.error(f"리뷰 코멘트 작성 실패: {e}")
            return False


class ClaudeReviewer:
    def __init__(self):
        self.claude_cli_timeout = int(os.getenv("CLAUDE_CLI_TIMEOUT", "60"))

    def test_connection(self) -> bool:
        """Claude CLI API 연결 테스트"""
        try:
            test_prompt = "간단히 '연결 확인됨'이라고 답해주세요."
            cmd = f"claude --print '{test_prompt}'"

            result = subprocess.run(
                cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, timeout=self.claude_cli_timeout
            )

            if result.returncode == 0:
                logger.info("Claude CLI API 연결 성공")
                return True
            else:
                logger.error(f"Claude CLI API 연결 실패: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Claude CLI API 호출 시간 초과")
            return False
        except Exception as e:
            logger.error(f"Claude CLI API 연결 테스트 실패: {e}")
            return False

    def review_code_change(self, file_path: str, diff_content: str, full_content: str = "") -> str:
        """Claude CLI API를 사용하여 코드 변경사항 리뷰"""

        # 특수 문자 이스케이프 처리
        escaped_diff = diff_content.replace("'", "'\"'\"'")
        escaped_path = file_path.replace("'", "'\"'\"'")
        escaped_full = full_content.replace("'", "'\"'\"'") if full_content else ""

        # 전체 파일 내용이 있으면 더 상세한 프롬프트 사용
        if full_content and len(full_content) > 50:
            prompt = f"""다음 코드 변경사항을 전체 파일 맥락과 함께 리뷰해주세요:

파일: {escaped_path}

현재 전체 파일 내용:
```
{escaped_full}
```

변경된 내용 (diff):
```diff
{escaped_diff}
```

전체 파일 맥락을 고려하여 다음 관점에서 리뷰해주세요:
1. 변경사항이 전체 코드 구조와 일관성이 있는지
2. 함수/변수명이 기존 코드 스타일과 맞는지
3. 의존성이나 호출 관계에 문제가 없는지
4. 버그 가능성이나 논리적 오류
5. 성능 이슈 및 보안 취약점
6. 테스트 필요성

구체적이고 실행 가능한 피드백을 제공해주세요. 문제가 없다면 '문제없음'이라고 답변해주세요."""
        else:
            prompt = f"""다음 코드 변경사항을 리뷰해주세요:

파일: {escaped_path}

변경된 내용:
```diff
{escaped_diff}
```

다음 관점에서 리뷰해주세요:
1. 버그 가능성이나 논리적 오류
2. 성능 이슈
3. 보안 취약점
4. 코딩 스타일 및 베스트 프랙티스
5. 테스트 필요성

구체적이고 실행 가능한 피드백을 제공해주세요. 문제가 없다면 '문제없음'이라고 답변해주세요."""

        try:
            # Claude CLI 명령 실행
            cmd = f"claude --print '{prompt}'"

            result = subprocess.run(
                cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, timeout=self.claude_cli_timeout
            )

            if result.returncode == 0:
                # JSON 응답 파싱 시도
                try:
                    response_data = json.loads(result.stdout)
                    if isinstance(response_data, list) and len(response_data) > 0:
                        # 마지막 assistant 메시지 찾기
                        for message in reversed(response_data):
                            if message.get("role") == "assistant":
                                return message.get("content", "응답 파싱 실패")
                    return result.stdout.strip()
                except json.JSONDecodeError:
                    # JSON이 아닌 경우 raw 텍스트 반환
                    return result.stdout.strip()
            else:
                logger.error(f"Claude CLI 호출 실패: {result.stderr}")
                return f"리뷰 생성 실패: {result.stderr}"

        except subprocess.TimeoutExpired:
            logger.error("Claude CLI 호출 시간 초과")
            return "리뷰 생성 시간 초과"
        except Exception as e:
            logger.error(f"Claude CLI 호출 실패: {e}")
            return f"리뷰 생성 중 오류 발생: {str(e)}"


class ReviewTracker:
    """리뷰 완료 추적을 위한 간단한 파일 기반 저장소"""

    def __init__(self, tracking_file: str = None):
        self.tracking_file = tracking_file or os.getenv("TRACKING_FILE", "reviewed_changes.txt")

    def is_reviewed(self, change_id: str, revision_id: str) -> bool:
        """이미 리뷰된 변경사항인지 확인"""
        tracking_key = f"{change_id}:{revision_id}"

        if not os.path.exists(self.tracking_file):
            return False

        with open(self.tracking_file, "r") as f:
            reviewed_changes = f.read().splitlines()

        return tracking_key in reviewed_changes

    def mark_reviewed(self, change_id: str, revision_id: str):
        """리뷰 완료로 표시"""
        tracking_key = f"{change_id}:{revision_id}"

        with open(self.tracking_file, "a") as f:
            f.write(f"{tracking_key}\n")


def should_review_file(file_path: str) -> bool:
    """리뷰해야 할 파일인지 판단"""
    # 리뷰 대상 파일 확장자 (확장됨)
    review_extensions = {
        ".py",
        ".java",
        ".js",
        ".ts",
        ".go",
        ".rs",
        ".cpp",
        ".c",
        ".h",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",  # Shell scripts
        ".yaml",
        ".yml",
        ".json",
        ".xml",
        ".toml",  # Configuration files
        ".dockerfile",
        ".containerfile",  # Docker files
        ".sql",
        ".md",
        ".txt",
        ".cfg",
        ".ini",
        ".conf",  # Other common files
        ".kt",
        ".scala",
        ".rb",
        ".php",
        ".swift",
        ".dart",  # Additional languages
    }

    # 제외할 패턴들
    exclude_patterns = [
        "test/",
        "tests/",
        "__pycache__/",
        "node_modules/",
        ".git/",
        "build/",
        "dist/",
        "target/",
        "generated/",
        "auto-generated",
    ]

    # 파일 확장자 확인
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension not in review_extensions:
        return False

    # 제외 패턴 확인
    for pattern in exclude_patterns:
        if pattern in file_path.lower():
            return False

    return True


def process_changes():
    """메인 처리 함수"""
    logger.info("변경사항 처리 시작")

    # .env에서 설정 읽기
    gerrit_host = os.getenv("GERRIT_HOST", "your-gerrit-server.com")
    gerrit_port = int(os.getenv("GERRIT_PORT", "29418"))
    gerrit_username = os.getenv("GERRIT_USERNAME", "nicolas.choi")
    ssh_key_path = os.path.expanduser(os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa"))

    gerrit = GerritAPI(gerrit_host, gerrit_port, gerrit_username, ssh_key_path)
    claude = ClaudeReviewer()
    tracker = ReviewTracker()

    # 최근 변경사항 조회 기간 설정
    query_age = os.getenv("GERRIT_QUERY_AGE", "")  # 기본값: 제한 없음
    if query_age:
        query = f"status:open NOT is:wip age:{query_age}"
    else:
        query = "status:open NOT is:wip"

    changes = gerrit.get_open_changes(query)
    logger.info(f"처리할 변경사항: {len(changes)}개")

    for change in changes:
        try:
            # 이미 리뷰된 변경사항인지 확인
            if tracker.is_reviewed(change.change_id, change.current_revision):
                logger.info(f"이미 리뷰됨: {change.subject}")
                continue

            logger.info(f"리뷰 시작: {change.subject}")

            # 현재 패치셋 번호 가져오기
            patchset_number = change.current_revision.split(",")[-1] if "," in change.current_revision else "1"

            # 변경된 파일 목록 가져오기
            files_info = gerrit.get_change_files(change.number)

            review_comments = []

            for file_path, file_info in files_info.items():
                # 리뷰 대상 파일인지 확인
                if not should_review_file(file_path):
                    continue

                # 파일 내용 가져오기 (큰 파일은 제외)
                max_lines_changed = int(os.getenv("MAX_LINES_CHANGED", "5000"))

                lines_changed = file_info.get("lines_inserted", 0) + file_info.get("lines_deleted", 0)
                if lines_changed > max_lines_changed:
                    logger.info(f"파일 변경 라인 수가 너무 큼, 스킵: {file_path} ({lines_changed} lines)")
                    continue

                # 파일의 diff 가져오기
                file_diff = gerrit.get_file_diff(change.number, patchset_number, file_path)

                if not file_diff:
                    continue

                # 전체 파일 내용 가져오기 (작은 파일만)
                full_content = ""
                try:
                    full_content = gerrit.get_file_content(change.number, file_path)
                    # 파일이 너무 크면 전체 내용 제외 (토큰 제한)
                    if len(full_content) > 10000:  # 10KB 제한
                        logger.info(f"파일이 너무 큼, 전체 내용 제외: {file_path} ({len(full_content)} chars)")
                        full_content = ""
                except Exception as e:
                    logger.debug(f"전체 파일 내용 가져오기 실패: {file_path}, {e}")

                # Claude 리뷰 요청
                review_result = claude.review_code_change(file_path, file_diff, full_content)

                if review_result and review_result.strip() != "문제없음":
                    review_comments.append(f"**{file_path}**\n{review_result}")

            # 리뷰 코멘트 작성
            if review_comments:
                combined_review = "🤖 **Claude 자동 코드 리뷰**\n\n" + "\n\n".join(review_comments)
                combined_review += "\n\n---\n*이 리뷰는 Claude AI에 의해 자동 생성되었습니다. 참고용으로만 사용하시고, 최종 판단은 사람이 해주세요.*"

                gerrit.post_review(change.number, patchset_number, combined_review)
                logger.info(f"리뷰 완료: {change.subject}")
            else:
                logger.info(f"리뷰할 내용 없음: {change.subject}")

            # 리뷰 완료 표시
            tracker.mark_reviewed(change.change_id, change.current_revision)

            # API 호출 제한을 위한 대기
            api_delay = int(os.getenv("API_DELAY_SECONDS", "2"))
            time.sleep(api_delay)

        except Exception as e:
            logger.error(f"변경사항 처리 중 오류: {change.subject}, 오류: {e}")

    logger.info("변경사항 처리 완료")


def test_connections():
    """시작 시 연결 테스트"""
    logger.info("연결 테스트 시작...")

    # .env에서 설정 읽기
    gerrit_host = os.getenv("GERRIT_HOST", "your-gerrit-server.com")
    gerrit_port = int(os.getenv("GERRIT_PORT", "29418"))
    gerrit_username = os.getenv("GERRIT_USERNAME", "nicolas.choi")
    ssh_key_path = os.path.expanduser(os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa"))

    # Gerrit SSH 연결 테스트
    try:
        gerrit = GerritAPI(gerrit_host, gerrit_port, gerrit_username, ssh_key_path)
        # version 명령으로 연결 테스트
        version_output = gerrit._run_ssh_command("version")
        logger.info(f"Gerrit SSH 연결 성공: {version_output.strip()}")
    except Exception as e:
        logger.error(f"Gerrit SSH 연결 실패: {e}")
        return False

    # Claude API 연결 테스트
    claude = ClaudeReviewer()
    if not claude.test_connection():
        return False

    logger.info("모든 연결 테스트 완료")
    return True


def main():
    """메인 함수 - 스케줄러 설정"""
    logger.info("Gerrit Claude 리뷰어 시작")

    # 연결 테스트
    if not test_connections():
        logger.error("연결 테스트 실패. 설정을 확인하고 다시 시도하세요.")
        return

    # 스케줄 설정 (.env에서 읽기)
    minute_interval = int(os.getenv("SCHEDULE_MINUTES", "30"))
    morning_time = os.getenv("SCHEDULE_MORNING", "09:00")
    afternoon_time = os.getenv("SCHEDULE_AFTERNOON", "14:00")

    schedule.every(minute_interval).minutes.do(process_changes)
    schedule.every().day.at(morning_time).do(process_changes)
    schedule.every().day.at(afternoon_time).do(process_changes)

    # 시작시 한 번 실행
    process_changes()

    # 스케줄러 실행
    check_interval = int(os.getenv("SCHEDULE_CHECK_SECONDS", "60"))
    error_retry_seconds = int(os.getenv("ERROR_RETRY_SECONDS", "300"))

    while True:
        try:
            schedule.run_pending()
            time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("프로그램 종료")
            break
        except Exception as e:
            logger.error(f"스케줄러 오류: {e}")
            time.sleep(error_retry_seconds)


if __name__ == "__main__":
    main()
