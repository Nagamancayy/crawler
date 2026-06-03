# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency files and install
COPY package*.json ./
RUN npm install

# Copy source and compile
COPY . .
RUN npm run build

# Nginx web server stage
FROM nginx:stable-alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy routing configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
