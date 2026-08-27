#!/usr/bin/env bash
# Dersper — geliştirme sunucusunu başlatır (backend + frontend).
# Bağımlılıkların kurulu olduğu varsayılır. Bkz. README.
set -euo pipefail
cd "$(dirname "$0")"

[[ -f .env ]] || { echo "HATA: .env yok. 'cp .env.example .env' ile oluşturup doldurun."; exit 1; }

# Sanal ortam varsa onu kullan, yoksa sistemdeki Python'a düş.
if [[ -x backend/.venv/bin/python ]]; then
  PY="$PWD/backend/.venv/bin/python"
else
  PY=$(command -v "${PYTHON:-python3.12}" || true)
  [[ -n "$PY" ]] || { echo "HATA: python3.12 bulunamadı."; exit 1; }
  echo "UYARI: backend/.venv yok, sistem Python'ı kullanılıyor."
fi

command -v npm >/dev/null || { echo "HATA: npm bulunamadı."; exit 1; }
[[ -d frontend/node_modules ]] || {
  echo "HATA: frontend bağımlılıkları kurulu değil. 'cd frontend && npm install' çalıştırın."
  exit 1
}

"$PY" -c "import fastapi, ortools, alembic" 2>/dev/null || {
  echo "HATA: backend bağımlılıkları eksik. 'backend/.venv/bin/pip install -r backend/requirements.txt' çalıştırın."
  exit 1
}

pids=()
cleanup() {
  trap - INT TERM EXIT
  [[ ${#pids[@]} -gt 0 ]] && kill "${pids[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "→ veritabanı şeması güncelleniyor"
(cd backend && "$PY" -m alembic.config upgrade head)

echo "→ backend  http://127.0.0.1:8000  (dokümantasyon: /docs)"
(cd backend && "$PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
pids+=($!)

echo "→ frontend http://localhost:5173"
(cd frontend && npm run dev) &
pids+=($!)

wait
