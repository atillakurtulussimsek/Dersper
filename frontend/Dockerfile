# Dersper arayüzü — Vite ile derlenir, nginx ile sunulur.
FROM node:20-alpine AS derleyici

WORKDIR /app

# Bağımlılıklar önce: kaynak değiştiğinde bu katman önbellekten gelir.
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=derleyici /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
