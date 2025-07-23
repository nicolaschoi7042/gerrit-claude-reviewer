#!/bin/bash
set -e

echo "Gerrit Claude 리뷰어 시작..."

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo "오류: .env 파일이 없습니다. .env.example을 복사하여 설정하세요."
    exit 1
fi

# Docker Compose로 실행
docker-compose up -d

echo "서비스가 시작되었습니다."
echo "로그 확인: docker-compose logs -f gerrit-claude-reviewer"
echo "중지: docker-compose down"