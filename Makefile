# Vuln Geeks Shop — Makefile
# Perintah tingkat-tinggi untuk menjalankan & mengelola lab.

COMPOSE ?= docker compose

.PHONY: up down reset seed test logs build

## up: bangun & jalankan seluruh lab (app di http://127.0.0.1:8000)
up:
	$(COMPOSE) up --build -d
	@echo "Lab jalan. Cek: curl http://127.0.0.1:8000/health"

## down: hentikan seluruh service (volume tetap)
down:
	$(COMPOSE) down

## build: rebuild image app
build:
	$(COMPOSE) build

## logs: ikuti log service app
logs:
	$(COMPOSE) logs -f app

## reset: kembalikan DB & file ke state bersih (buang volume) lalu seed ulang
reset:
	$(COMPOSE) down -v
	$(COMPOSE) up --build -d
	$(MAKE) seed
	@echo "Reset selesai — state bersih."

## seed: isi data awal deterministik (P0: masih no-op)
seed:
	$(COMPOSE) run --rm app python -m seed.seed

## test: jalankan pytest di dalam container app
test:
	$(COMPOSE) run --rm app pytest -q
