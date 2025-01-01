mkdir -p deployment/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/certs/local-dev.key \
  -out deployment/certs/local-dev.crt \
  -subj "/CN=localhost"
