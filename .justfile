# Justfile to manage frontend, backend, and db

docker_compose := "docker-compose.yml"

# Start all containers
start:
  docker compose -f {{docker_compose}} up -d --build

# Stop all containers
stop:
  docker compose -f {{docker_compose}} down

# Restart all containers 
restart:
 @just stop 
 @just start

# View logs
logs:
  docker compose -f {{docker_compose}} logs -f

# Backend shell
bash-backend:
  docker compose -f {{docker_compose}} exec backend bash

# DB shell
bash-db:
  docker compose -f {{docker_compose}} exec db psql -U fastapi_user -d smartaama

# Run migrations
migrate:
  docker compose -f {{docker_compose}} exec backend alembic upgrade head

# Create new migration
makemigration message:
  docker compose -f {{docker_compose}} exec backend alembic revision --autogenerate -m "{{message}}"
