#!/bin/sh
set -eu

PROJECT_DIR="${PROJECT_DIR:-/opt/edu-mvp}"
PUBLIC_IP="43.128.141.25"

/usr/bin/docker run --rm \
    -v "$PROJECT_DIR/web:/var/www/html" \
    -v "$PROJECT_DIR/certbot/conf:/etc/letsencrypt" \
    certbot/certbot:latest certonly \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    --preferred-profile shortlived \
    --webroot \
    --webroot-path /var/www/html \
    --cert-name "$PUBLIC_IP" \
    --ip-address 43.128.141.25 \
    --keep-until-expiring

/usr/bin/docker exec edu-web nginx -s reload
