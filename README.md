# Gerrit Claude 리뷰어 설치 및 실행 가이드

## 1. 사전 준비사항

### Gerrit 설정
1. **SSH 키 설정**
   - SSH 키 생성: `ssh-keygen -t rsa -b 4096 -C "claude-reviewer@example.com"`
   - 공개 키를 Gerrit에 등록: Gerrit 웹 인터페이스 → Settings → SSH Keys
   - 개인 키 위치 확인 (기본: `~/.ssh/id_rsa`)

2. **리뷰어 계정 설정**
   - 전용 계정 생성 권장 (예: `claude-reviewer`)
   - 필요한 권한: 코드 리뷰 읽기/쓰기, 변경사항 조회
   - SSH 접근 권한 필요

### Claude API 키 준비
- Anthropic Console에서 API 키 발급
- 충분한 크레딧 확인

## 2. 설치 방법

### 방법 1: Docker 사용 (권장)

```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd gerrit-claude-reviewer

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어서 실제 값들로 수정
# 애플리케이션이 자동으로 .env 파일을 읽어옵니다

# 3. 설정 파일 수정
cp config.yaml.example config.yaml
# config.yaml에서 Gerrit URL 등 필요한 설정 수정

# 4. 실행
chmod +x start.sh
./start.sh
```

### 방법 2: 직접 Python 실행

```bash
# 1. Python 3.8+ 설치 확인
python3 --version

# 2. 가상 환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정 (.env 파일 생성)
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 수정:
# GERRIT_HOST=your-gerrit-server.com
# GERRIT_PORT=29418
# GERRIT_USERNAME=claude-reviewer
# SSH_KEY_PATH=~/.ssh/id_rsa
# CLAUDE_API_KEY=your-api-key

# 5. 실행
python gerrit_claude_reviewer.py
```

## 3. 설정 상세

### 연결 테스트
```bash
# 통합 연결 테스트 (권장)
python test_connections.py

# 수동 Gerrit SSH 연결 확인
ssh -p 29418 claude-reviewer@your-gerrit-server.com gerrit version

# 수동 변경사항 조회 테스트
ssh -p 29418 claude-reviewer@your-gerrit-server.com gerrit query --format=JSON status:open limit:1
```

**중요**: Claude API URL (`https://api.anthropic.com/v1/messages`)에 직접 접근하면 "Method Not Allowed" 오류가 나타나는 것이 정상입니다. 이는 GET 요청을 허용하지 않기 때문이며, POST 요청으로만 접근 가능합니다.

### 스케줄 설정
config.yaml에서 스케줄 조정:
```yaml
schedule:
  - interval: 30        # 30분마다
    unit: "minutes"
  - time: "09:00"      # 매일 오전 9시
    unit: "daily"
```

### 파일 필터링 설정
```yaml
file_filters:
  include_extensions:
    - ".py"
    - ".java"
    - ".js"
  exclude_patterns:
    - "test/"
    - "generated/"
  max_lines_changed: 500
```

## 4. 운영 방법

### 로그 모니터링
```bash
# Docker 사용시
docker-compose logs -f gerrit-claude-reviewer

# 직접 실행시
tail -f gerrit_claude_reviewer.log
```

### 상태 확인
```bash
# 프로세스 확인
docker-compose ps

# 리뷰 추적 파일 확인
cat reviewed_changes.txt
```

### 문제 해결
```bash
# 컨테이너 재시작
docker-compose restart gerrit-claude-reviewer

# 설정 변경 후 재시작
docker-compose down
docker-compose up -d
```

## 5. 고급 설정

### 큐 시스템 사용 (대용량 처리)
Redis와 Celery를 사용한 비동기 처리:

```python
# celery_worker.py
from celery import Celery

app = Celery('gerrit_reviewer')
app.config_from_object('celeryconfig')

@app.task
def review_change_async(change_data):
    # 비동기 리뷰 처리
    pass
```

### 데이터베이스 연동
SQLite 대신 PostgreSQL 사용:

```yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "gerrit_reviewer"
  username: "${DB_USERNAME}"
  password: "${DB_PASSWORD}"
```

### 알림 시스템
Slack 알림 설정:

```yaml
notifications:
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#code-review"
```

## 6. 보안 고려사항

### 권한 최소화
- 리뷰어 계정에 최소 필요 권한만 부여
- API 키는 환경 변수로만 관리
- 네트워크 접근 제한

### 모니터링
- 로그 정기 검토
- API 사용량 모니터링
- 에러 알림 설정

## 7. 유지보수

### 정기 작업
```bash
# 로그 파일 정리 (매주)
find /app/logs -name "*.log" -mtime +7 -delete

# 리뷰 추적 파일 정리 (매월)
# 오래된 항목 제거
```

### 업데이트
```bash
# 코드 업데이트
git pull origin main

# 컨테이너 재빌드
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 트러블슈팅

#### 일반적인 문제들
1. **Gerrit SSH 연결 실패**
   - SSH 키 경로 확인 (`~/.ssh/id_rsa` 존재 여부)
   - SSH 키 권한 확인 (`chmod 600 ~/.ssh/id_rsa`)
   - Gerrit에 공개키 등록 확인
   - 네트워크 연결 및 포트(29418) 확인
   - 계정 권한 확인

2. **Claude API 호출 실패**
   - API 키 유효성 확인 (`test_connections.py` 실행)
   - 크레딧 잔액 확인 (Anthropic Console)
   - 요청 제한 확인 (rate limiting)
   - 네트워크 방화벽/프록시 설정 확인
   - API 키가 올바른 형식인지 확인 (sk-ant-로 시작)

3. **메모리 부족**
   - Docker 메모리 제한 증가
   - 파일 크기 제한 조정
   - 배