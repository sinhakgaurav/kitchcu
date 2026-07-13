# Build stage
FROM node:22-alpine AS build
ARG APP=customer
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG VITE_CUSTOMER_APP_URL=http://localhost:13001
ARG VITE_KITCHEN_APP_URL=http://localhost:13002
ARG VITE_ADMIN_APP_URL=http://localhost:13003
ENV VITE_CUSTOMER_APP_URL=$VITE_CUSTOMER_APP_URL
ENV VITE_KITCHEN_APP_URL=$VITE_KITCHEN_APP_URL
ENV VITE_ADMIN_APP_URL=$VITE_ADMIN_APP_URL
RUN if [ "$APP" = "customer" ]; then npm run build:customer; \
    elif [ "$APP" = "kitchen" ]; then npm run build:kitchen; \
    elif [ "$APP" = "admin" ]; then npm run build:admin; \
    elif [ "$APP" = "portal" ]; then npm run build:portal; \
    else echo "Unknown APP=$APP" && exit 1; fi

# Serve stage
FROM nginx:alpine
ARG APP=customer
COPY nginx.${APP}.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/${APP} /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
