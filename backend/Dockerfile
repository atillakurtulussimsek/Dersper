# Dersper — tek imaj: arayüz derlenir, FastAPI hem /api'yi hem arayüzü sunar.
#
# Tek konteyner olmasının sebebi: ayrı bir web sunucusu ve konteynerler arası ağ
# gerektirmez. Böylece tek alan adı yeter, CORS ayarı gerekmez ve dağıtımda
# kırılabilecek katman sayısı en aza iner.
#
# Derleme bağlamı deponun KÖKÜDÜR (hem backend/ hem frontend/ gerekir):
#   docker build -f backend/Dockerfile .

# NOT: Arayüz Metronic 8 temasını kullanır ve tema tescilli olduğu için depoda
# bulunmaz. İmajı kurmadan önce `cd frontend && npm run tema:kur` çalıştırın;
# betik lisanslı kopyanızdan tek CSS dosyasını frontend/public/metronic/ altına
# koyar ve derleme onu buraya taşır. Atlanırsa arayüz biçimsiz derlenir.
FROM node:20-alpine AS arayuz

WORKDIR /arayuz
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


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
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Derlenmiş arayüz; uygulama burayı bulursa kendisi sunar.
COPY --from=arayuz /arayuz/dist ./app/static

# Kök olmayan kullanıcı.
RUN useradd --system --create-home dersper && chown -R dersper:dersper /app
USER dersper

EXPOSE 8000

# Açılışta şema güncellenir, sonra sunucu başlar. Migration başarısız olursa
# konteyner ayağa kalkmaz — yarım şemayla çalışmaktansa durmak yeğdir.
CMD ["sh", "-c", "python -m alembic.config upgrade head && exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]
