# Dockerfile for Frontend (Vanilla HTML/JS/CSS)
FROM nginx:alpine

# Copy source code to Nginx serving directory
COPY frontend/ /usr/share/nginx/html/

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
