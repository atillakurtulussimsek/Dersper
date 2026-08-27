#!/usr/bin/env bash
# Dersper — geliştirme sunucusunu başlatır (backend + frontend).
# Bağımlılıkların kurulu olduğu varsayılır. Bkz. README.
set -euo pipefail
cd "$(dirname "$0")"

[[ -f .env ]] || { echo "HATA: .env yok. 'cp .env.example .env' ile oluşturup doldurun."; exit 1; }

PY=${PYTHON:-python3.12}
command -v "$PY" >/dev/null || { echo "HATA: $PY bulunamadı."; exit 1; }
command -v npm  >/dev/null || { echo "HATA: npm bulunamadı."; exit 1; }

pids=()
cleanup() { trap - INT TERM EXIT; kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup INT TERM EXIT

echo "→ veritabanı şeması güncelleniyor"
(cd backend && "$PY" -m alembic upgrade head)

echo "→ backend  http://127.0.0.1:8000  (dokümantasyon: /docs)"
(cd backend && "$PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
pids+=($!)

echo "→ frontend http://localhost:5173"
(cd frontend && npm run dev) &
pids+=($!)

wait -n
