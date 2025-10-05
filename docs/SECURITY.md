# Security Guide

## Overview

This document outlines security best practices and configurations for the Baseball Simulation system.

---

## 🔐 Authentication & Authorization

### API Key Authentication (Recommended for Production)

The system supports API key-based authentication for external integrations.

#### Generating API Keys

```bash
# Generate a secure API key
openssl rand -hex 32

# Example output:
# a7f3d8e9c2b1f4a6e8d7c3b9f2a1e5d8c4b7f9a2e6d1c8b3f5a9e7d2c6b4f1a8
```

#### Configuring API Keys

Add to your `.env` file:

```bash
API_KEY_ADMIN=<your-generated-admin-key>
API_KEY_READONLY=<your-generated-readonly-key>
```

#### Using API Keys

Include the API key in request headers:

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8080/api/v1/teams
```

#### API Key Permissions

- **Admin Key**: Full access (read/write)
- **Readonly Key**: Read-only access to data

---

## 🛡️ Rate Limiting

Rate limiting protects against abuse and DDoS attacks.

### Current Configuration

- **Limit**: 100 requests per minute per IP
- **Burst**: 200 requests
- **Response**: `429 Too Many Requests` when exceeded

### Configuring Rate Limits

In `.env`:

```bash
API_RATE_LIMIT=100  # requests per minute
API_RATE_BURST=200  # burst capacity
```

---

## 🔒 TLS/HTTPS Configuration

### Local Development

For local development, HTTP is acceptable. Use the provided Docker Compose setup.

### Production Deployment

**IMPORTANT**: Always use HTTPS in production!

#### Option 1: Reverse Proxy (Recommended)

Use nginx or Caddy as a reverse proxy with automatic TLS:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourbaseballsim.com;

    ssl_certificate /etc/ssl/certs/baseball-sim.crt;
    ssl_certificate_key /etc/ssl/private/baseball-sim.key;

    # Security headers (already set by API, but belt-and-suspenders)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://api-gateway:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Option 2: Let's Encrypt with Caddy

Create `Caddyfile`:

```
api.yourbaseballsim.com {
    reverse_proxy api-gateway:8080
    tls your-email@example.com
}
```

---

## 🔑 Secrets Management

### Environment Variables (Basic)

Store secrets in `.env` file (never commit to git):

```bash
# Add to .gitignore
.env
.env.local
.env.production
```

### HashiCorp Vault (Advanced - Production)

For production systems with many secrets:

#### 1. Setup Vault

```bash
docker run -d --name=vault \
  --cap-add=IPC_LOCK \
  -p 8200:8200 \
  vault:latest
```

#### 2. Initialize and Unseal

```bash
docker exec vault vault operator init
# Save the unseal keys and root token!

docker exec vault vault operator unseal <key-1>
docker exec vault vault operator unseal <key-2>
docker exec vault vault operator unseal <key-3>
```

#### 3. Store Secrets

```bash
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='<your-root-token>'

vault kv put secret/baseball-sim/database \
  password="secure-db-password"

vault kv put secret/baseball-sim/api-keys \
  admin="admin-api-key" \
  readonly="readonly-api-key"
```

#### 4. Configure Application

In `.env`:

```bash
VAULT_ENABLED=true
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=<app-token>
VAULT_SECRET_PATH=secret/baseball-sim
```

---

## 🔍 Security Headers

The following security headers are automatically added by the API Gateway:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS protection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer control |
| `Content-Security-Policy` | Configured | XSS/injection prevention |

---

## 🚨 Security Checklist

### Pre-Production

- [ ] Change all default passwords
- [ ] Generate strong API keys
- [ ] Set `DEBUG=false`
- [ ] Configure TLS/HTTPS
- [ ] Review CORS origins
- [ ] Enable rate limiting
- [ ] Set up monitoring/alerting
- [ ] Review database permissions
- [ ] Enable audit logging

### Production

- [ ] Use secrets manager (Vault)
- [ ] Regular security updates
- [ ] Monitor rate limit violations
- [ ] Review logs for suspicious activity
- [ ] Backup encryption keys
- [ ] Test disaster recovery
- [ ] Penetration testing
- [ ] Security audit

---

## 🔐 Password Requirements

### Database Passwords

- Minimum 16 characters
- Mix of uppercase, lowercase, numbers, symbols
- No dictionary words
- Rotate every 90 days

### API Keys

- Minimum 32 bytes (64 hex characters)
- Generated using cryptographically secure RNG
- Never hardcode in application code
- Rotate quarterly

---

## 🚫 What NOT To Do

❌ **Never commit secrets to Git**
❌ **Never use default passwords in production**
❌ **Never disable HTTPS in production**
❌ **Never log sensitive data (passwords, keys)**
❌ **Never expose database directly to internet**
❌ **Never trust client input without validation**
❌ **Never run containers as root**

---

## 📊 Monitoring Security Events

### Metrics to Track

- Failed authentication attempts
- Rate limit violations
- Unusual traffic patterns
- Database connection failures
- API error rates

### Alerting Rules (Prometheus)

See `prometheus/alerts.yml` for configured alerts.

---

## 🆘 Incident Response

### If You Suspect a Breach

1. **Immediately rotate all API keys and passwords**
2. **Check logs for unauthorized access**
3. **Review recent database changes**
4. **Notify stakeholders**
5. **Document timeline of events**
6. **Patch vulnerabilities**
7. **Post-mortem and lessons learned**

### Emergency Contacts

- Security Team: security@yourcompany.com
- Database Admin: dba@yourcompany.com
- DevOps Lead: devops@yourcompany.com

---

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
- [Go Security Checklist](https://github.com/guardrailsio/awesome-golang-security)

---

**Last Updated**: 2025-10-05
**Next Review**: 2026-01-05
