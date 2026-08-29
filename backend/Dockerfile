# Dersper backend — FastAPI + OR-Tools + WeasyPrint
FROM python:3.12-slim

# WeasyPrint PDF üretimi için sistem kütüphaneleri (pango/cairo) ve Türkçe
# karakterleri kapsayan bir yazı tipi. Bunlar olmadan PDF ucu 503 döner.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Bağımlılıklar önce: kod değiştiğinde bu katman önbellekten gelir.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Kök olmayan kullanıcı.
RUN useradd --system --create-home dersper && chown -R dersper:dersper /app
USER dersper

EXPOSE 8000

# Açılışta şema güncellenir, sonra sunucu başlar. Migration başarısız olursa
# konteyner ayağa kalkmaz — yarım şemayla çalışmaktansa durmak yeğdir.
CMD ["sh", "-c", "python -m alembic.config upgrade head && exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
