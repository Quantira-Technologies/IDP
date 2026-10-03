# intel2doc — common developer tasks.
# On Windows, run the equivalent PowerShell shown in the README if `make` is unavailable.

.PHONY: install test backend frontend up down build clean

install:
	cd backend && python -m venv .venv && ./.venv/Scripts/pip install -r requirements.txt
	cd frontend && npm install

test:
	cd backend && ./.venv/Scripts/python -m pytest -q

backend:
	cd backend && ./.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

up:
	docker compose up --build

down:
	docker compose down

build:
	cd frontend && npm run build
	cd backend && ./.venv/Scripts/python -m pytest -q

clean:
	docker compose down -v
