# syntax=docker/dockerfile:1

# ─── deps ──────────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
# Solo los manifiestos: un cambio en src/ no reinstala node_modules.
COPY package.json package-lock.json* ./
# npm ci exige lockfile; todavía no existe en el scaffold inicial. Después del
# primer `docker compose up`, commiteá el package-lock.json que queda generado
# y esto pasa a ser una instalación reproducible.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# ─── dev ───────────────────────────────────────────────────────────────────
FROM node:20-alpine AS dev
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# ─── build ─────────────────────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ─── prod ──────────────────────────────────────────────────────────────────
# nginx sirve los estáticos y hace de proxy a /api, para que el código del front
# siga usando rutas relativas igual que en dev.
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
# El entrypoint de la imagen oficial expande las variables de los .template
# en /etc/nginx/templates y deja el resultado en /etc/nginx/conf.d.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
# Sin el filtro, envsubst se comería también las variables propias de nginx
# ($host, $uri, $upstream...). Solo se expanden estas tres.
ENV NGINX_ENVSUBST_FILTER='^(BACKEND_URL|PORT|NGINX_LOCAL_RESOLVERS)$'
# El script 15-local-resolvers.envsh de la imagen oficial, que exporta
# NGINX_LOCAL_RESOLVERS leyendo /etc/resolv.conf, es opt-in: sin esta variable
# hace `return 0` y el resolver del template queda sin expandir.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1
# Defaults para correr la imagen sola; en Railway los pisan las variables del
# servicio: PORT lo inyecta la plataforma y BACKEND_URL apunta al dominio interno.
ENV PORT=80
ENV BACKEND_URL=http://backend:8000
EXPOSE 80
