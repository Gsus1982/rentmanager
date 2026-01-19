#!/bin/bash
set -e

echo "RentManager Setup - macOS"

if ! command -v docker &> /dev/null; then
    echo "Docker no está instalado."
    exit 1
fi

if ! docker-compose --version &> /dev/null; then
    echo "Docker Compose no está instalado."
    exit 1
fi

docker-compose build
docker-compose up -d

sleep 5

docker-compose exec web python manage.py createsuperuser
