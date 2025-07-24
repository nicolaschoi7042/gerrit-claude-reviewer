FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    wget \
    vim \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 로그 및 SSH 디렉토리 생성
RUN mkdir -p /app/logs /app/.ssh

# Node.js 설치 (NodeSource 공식 스크립트 사용)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# 비root 사용자 생성 및 sudo 권한 부여
RUN useradd -m -u 1000 reviewer \
    && echo "reviewer ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Claude CLI 전역 설치
RUN npm install -g @anthropic-ai/claude-code

# 권한 설정 (사용자 전환 전에)
RUN chown -R reviewer:reviewer /app
RUN chmod 755 /app/logs
RUN chmod 700 /app/.ssh

USER reviewer

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# 실행
CMD ["./scripts/startup.sh"]
