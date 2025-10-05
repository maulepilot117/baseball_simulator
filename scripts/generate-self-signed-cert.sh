#!/bin/bash
# Generate self-signed SSL certificate for local development
# For production, use Let's Encrypt or a proper CA

set -e

CERT_DIR="./nginx/ssl"
DOMAIN="baseball-sim.local"

echo "Generating self-signed SSL certificate for $DOMAIN..."

# Create directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Generate private key
openssl genrsa -out "$CERT_DIR/key.pem" 2048

# Generate certificate signing request
openssl req -new -key "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.csr" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"

# Generate self-signed certificate (valid for 1 year)
openssl x509 -req -days 365 \
    -in "$CERT_DIR/cert.csr" \
    -signkey "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem"

# Set proper permissions
chmod 600 "$CERT_DIR/key.pem"
chmod 644 "$CERT_DIR/cert.pem"

echo "✓ Certificate generated successfully!"
echo ""
echo "Certificate: $CERT_DIR/cert.pem"
echo "Private Key: $CERT_DIR/key.pem"
echo ""
echo "⚠️  This is a SELF-SIGNED certificate for DEVELOPMENT only!"
echo "For production, use Let's Encrypt or a proper CA."
echo ""
echo "To trust this certificate locally (macOS):"
echo "sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_DIR/cert.pem"
