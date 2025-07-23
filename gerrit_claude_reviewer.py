#!/usr/bin/env python3
"""
Gerrit Claude 리뷰어 - 스케줄러 기반
"""

import subprocess
import json
import time
import logging
from datetime import datetime, timedelta
import base64
from typing import List, Dict, Optional
import schedule
import os
from dataclasses import dataclass
import tempfile
import shlex
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService

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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
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
            'ssh',
            '-p', str(self.port),
            '-i', self.ssh_key_path,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            f'{self.username}@{self.host}',
            'gerrit',
            gerrit_command
        ]
        
        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"SSH command failed: {e.stderr}")
            raise
    
    def get_open_changes(self, query: str = "status:open") -> List[Change]:
        """열려있는 변경사항 목록 가져오기"""
        # query 명령어로 변경사항 조회
        command = f'query --format=JSON --current-patch-set {shlex.quote(query)}'
        
        try:
            output = self._run_ssh_command(command)
            
            changes = []
            for line in output.strip().split('\n'):
                if not line:
                    continue
                    
                data = json.loads(line)
                
                # 마지막 라인은 통계 정보이므로 제외
                if 'type' in data and data['type'] == 'stats':
                    continue
                
                if 'number' in data:
                    changes.append(Change(
                        change_id=data.get('id', ''),
                        number=str(data['number']),
                        subject=data.get('subject', ''),
                        owner=data.get('owner', {}),
                        status=data.get('status', ''),
                        current_revision=data.get('currentPatchSet', {}).get('revision', ''),
                        updated=data.get('lastUpdated', '')
                    ))
            
            return changes
            
        except Exception as e:
            logger.error(f"Gerrit query failed: {e}")
            return []
    
    def get_change_files(self, change_number: str, patchset_number: str = None) -> Dict:
        """특정 변경사항의 파일 목록 가져오기"""
        if patchset_number:
            command = f'query --files --patch-sets change:{change_number} --format=JSON'
        else:
            command = f'query --files --current-patch-set change:{change_number} --format=JSON'
        
        try:
            output = self._run_ssh_command(command)
            
            for line in output.strip().split('\n'):
                if not line:
                    continue
                    
                data = json.loads(line)
                
                # 통계 정보 제외
                if 'type' in data and data['type'] == 'stats':
                    continue
                
                # 파일 정보 추출
                if 'currentPatchSet' in data:
                    files = data['currentPatchSet'].get('files', [])
                    file_dict = {}
                    for file_info in files:
                        if file_info['file'] != '/COMMIT_MSG':
                            file_dict[file_info['file']] = {
                                'lines_inserted': file_info.get('insertions', 0),
                                'lines_deleted': file_info.get('deletions', 0),
                                'type': file_info.get('type', 'MODIFIED')
                            }
                    return file_dict
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get file list: {e}")
            return {}
    
    def get_file_diff(self, change_number: str, patchset_number: str, file_path: str) -> str:
        """파일의 변경 diff 가져오기"""
        # scp 명령을 사용하여 patch 파일 다운로드
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.patch') as tmp_file:
            scp_command = [
                'scp',
                '-P', str(self.port),
                '-i', self.ssh_key_path,
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                f'{self.username}@{self.host}:changes/{change_number}/{patchset_number}/patch',
                tmp_file.name
            ]
            
            try:
                subprocess.run(scp_command, check=True, capture_output=True, text=True)
                
                # patch 파일에서 특정 파일의 diff만 추출
                with open(tmp_file.name, 'r') as f:
                    patch_content = f.read()
                
                # 파일별 diff 추출 로직
                file_diff = self._extract_file_diff(patch_content, file_path)
                return file_diff
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to download patch: {e}")
                return ""
            finally:
                # 임시 파일 삭제
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)
    
    def _extract_file_diff(self, patch_content: str, file_path: str) -> str:
        """전체 패치에서 특정 파일의 diff 추출"""
        lines = patch_content.split('\n')
        file_diff = []
        in_target_file = False
        
        for i, line in enumerate(lines):
            if line.startswith('diff --git'):
                if f'b/{file_path}' in line:
                    in_target_file = True
                else:
                    if in_target_file:
                        break
                    in_target_file = False
            
            if in_target_file:
                file_diff.append(line)
        
        return '\n'.join(file_diff)
    
    def post_review(self, change_number: str, patchset_number: str, message: str, score: int = 0):
        """리뷰 코멘트 작성"""
        # 메시지에서 특수 문자 이스케이프
        escaped_message = shlex.quote(message)
        
        # review 명령어 구성
        command = f'review --message {escaped_message}'
        
        # Code-Review 점수 추가 (있는 경우)
        if score != 0:
            command += f' --code-review {score}'
        
        # 변경사항 지정
        command += f' {change_number},{patchset_number}'
        
        try:
            output = self._run_ssh_command(command)
            logger.info(f"리뷰 코멘트 작성 완료: {change_number}")
            return True
            
        except Exception as e:
            logger.error(f"리뷰 코멘트 작성 실패: {e}")
            return False

class ClaudeReviewer:
    def __init__(self):
        self.claude_url = os.getenv("CLAUDE_WEB_URL", "https://claude.ai")
        self.chrome_driver_path = os.getenv("CHROME_DRIVER_PATH", "/usr/bin/chromedriver")
        self.driver = None
    
    def test_connection(self) -> bool:
        """Claude 웹사이트 연결 및 로그인 테스트"""
        try:
            self._init_driver()
            
            # 자동 로그인 시도
            if not self._login_to_claude():
                return False
            
            logger.info("Claude 웹사이트 연결 및 로그인 성공")
            return True
            
        except Exception as e:
            logger.error(f"Claude 웹사이트 연결 테스트 실패: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def _init_driver(self):
        """웹 드라이버 초기화"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 백그라운드 실행
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # ChromeDriver 경로 설정
        service = ChromeService(executable_path=self.chrome_driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def _login_to_claude(self):
        """Claude 웹사이트에 자동 로그인"""
        try:
            email = os.getenv("CLAUDE_EMAIL")
            password = os.getenv("CLAUDE_PASSWORD")
            
            if not email or not password:
                logger.error("Claude 로그인 정보가 설정되지 않았습니다 (.env 파일의 CLAUDE_EMAIL, CLAUDE_PASSWORD 확인)")
                return False
            
            logger.info("Claude 웹사이트 로그인 시도...")
            
            # 로그인 페이지로 이동
            self.driver.get(f"{self.claude_url}/login")
            
            # 이메일 입력
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], #email"))
            )
            email_input.clear()
            email_input.send_keys(email)
            
            # 비밀번호 입력
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password'], #password")
            password_input.clear()
            password_input.send_keys(password)
            
            # 로그인 버튼 클릭
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .login-button, input[type='submit']")
            login_button.click()
            
            # 로그인 완료 대기 (대시보드나 채팅 페이지 로딩 확인)
            WebDriverWait(self.driver, 15).until(
                lambda driver: "/chat" in driver.current_url or "dashboard" in driver.current_url or "claude.ai/chats" in driver.current_url
            )
            
            logger.info("Claude 웹사이트 로그인 성공")
            return True
            
        except Exception as e:
            logger.error(f"Claude 웹사이트 로그인 실패: {e}")
            return False
        
    def review_code_change(self, file_path: str, diff_content: str, full_content: str = "") -> str:
        """Claude 웹사이트를 사용하여 코드 변경사항 리뷰"""
        
        prompt = f"""다음 코드 변경사항을 리뷰해주세요:

파일: {file_path}

변경된 내용:
```diff
{diff_content}
```

다음 관점에서 리뷰해주세요:
1. 버그 가능성이나 논리적 오류
2. 성능 이슈
3. 보안 취약점
4. 코딩 스타일 및 베스트 프랙티스
5. 테스트 필요성

구체적이고 실행 가능한 피드백을 제공해주세요. 문제가 없다면 '문제없음'이라고 답변해주세요."""

        try:
            self._init_driver()
            
            # 자동 로그인
            if not self._login_to_claude():
                return "로그인 실패로 인한 리뷰 생성 불가"
            
            # 새 대화 시작
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "textarea"))
            )
            
            # 텍스트 입력
            textarea = self.driver.find_element(By.TAG_NAME, "textarea")
            textarea.clear()
            textarea.send_keys(prompt)
            
            # 전송 버튼 클릭 (실제 셀렉터는 사이트에 따라 다를 수 있음)
            send_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .send-button, [aria-label*='send'], [aria-label*='Send']")
            send_button.click()
            
            # 응답 대기
            time.sleep(5)  # 응답 생성 대기
            
            # 응답 텍스트 추출 (실제 셀렉터는 사이트에 따라 다를 수 있음)
            response_elements = self.driver.find_elements(By.CSS_SELECTOR, ".message-content, .response, .assistant-message")
            
            if response_elements:
                return response_elements[-1].text  # 마지막 응답 반환
            else:
                logger.error("Claude 응답을 찾을 수 없음")
                return "리뷰 생성 중 응답을 찾을 수 없음"
            
        except Exception as e:
            logger.error(f"Claude 웹사이트 호출 실패: {e}")
            return f"리뷰 생성 중 오류 발생: {str(e)}"
        finally:
            if self.driver:
                self.driver.quit()

class ReviewTracker:
    """리뷰 완료 추적을 위한 간단한 파일 기반 저장소"""
    
    def __init__(self, tracking_file: str = None):
        self.tracking_file = tracking_file or os.getenv("TRACKING_FILE", "reviewed_changes.txt")
        
    def is_reviewed(self, change_id: str, revision_id: str) -> bool:
        """이미 리뷰된 변경사항인지 확인"""
        tracking_key = f"{change_id}:{revision_id}"
        
        if not os.path.exists(self.tracking_file):
            return False
            
        with open(self.tracking_file, 'r') as f:
            reviewed_changes = f.read().splitlines()
            
        return tracking_key in reviewed_changes
    
    def mark_reviewed(self, change_id: str, revision_id: str):
        """리뷰 완료로 표시"""
        tracking_key = f"{change_id}:{revision_id}"
        
        with open(self.tracking_file, 'a') as f:
            f.write(f"{tracking_key}\n")

def should_review_file(file_path: str) -> bool:
    """리뷰해야 할 파일인지 판단"""
    # 리뷰 대상 파일 확장자
    review_extensions = {'.py', '.java', '.js', '.ts', '.go', '.rs', '.cpp', '.c', '.h'}
    
    # 제외할 패턴들
    exclude_patterns = [
        'test/', 'tests/', '__pycache__/', 'node_modules/', 
        '.git/', 'build/', 'dist/', 'target/',
        'generated/', 'auto-generated'
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
    gerrit_username = os.getenv("GERRIT_USERNAME", "claude-reviewer")
    ssh_key_path = os.path.expanduser(os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa"))
    
    gerrit = GerritAPI(gerrit_host, gerrit_port, gerrit_username, ssh_key_path)
    claude = ClaudeReviewer()
    tracker = ReviewTracker()
    
    # 최근 변경사항 조회 기간 설정
    query_age = os.getenv("GERRIT_QUERY_AGE", "1d")  # 기본값: 1일
    query = f"status:open age:{query_age}"
    
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
            patchset_number = change.current_revision.split(',')[-1] if ',' in change.current_revision else '1'
            
            # 변경된 파일 목록 가져오기
            files_info = gerrit.get_change_files(change.number)
            
            review_comments = []
            
            for file_path, file_info in files_info.items():
                # 리뷰 대상 파일인지 확인
                if not should_review_file(file_path):
                    continue
                
                # 파일 내용 가져오기 (큰 파일은 제외)
                max_lines_changed = int(os.getenv("MAX_LINES_CHANGED", "500"))
                if file_info.get('lines_inserted', 0) + file_info.get('lines_deleted', 0) > max_lines_changed:
                    logger.info(f"파일이 너무 큼, 스킵: {file_path}")
                    continue
                
                # 파일의 diff 가져오기
                file_diff = gerrit.get_file_diff(change.number, patchset_number, file_path)
                
                if not file_diff:
                    continue
                
                # Claude 리뷰 요청
                review_result = claude.review_code_change(file_path, file_diff)
                
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
    gerrit_username = os.getenv("GERRIT_USERNAME", "claude-reviewer")
    ssh_key_path = os.path.expanduser(os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa"))
    
    # Gerrit SSH 연결 테스트
    try:
        gerrit = GerritAPI(gerrit_host, gerrit_port, gerrit_username, ssh_key_path)
        # version 명령으로 연결 테스트
        version_output = gerrit._run_ssh_command('version')
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