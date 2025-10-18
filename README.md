This web application provides authentication (password + OAuth Google/Twitter), product management (Products), and a role model (buyer/seller/admin).
- Framework: FastAPI
- Storage: PostgreSQL (asyncpg), schema applied from install/schema.sql.
- Deployment: Docker Compose (app + postgres), and locally via systemd unit (uvicorn).
- Key security practices: short-lived JWT, refresh via HttpOnly cookie, PKCE + state for OAuth, password hashing (bcrypt), hashing of refresh tokens in DB, strict cookie flags, CORS/CSRF, permission checks in the service layer.
- Observability: structured logs, health endpoint, plan to add metrics and tracing (Prometheus + OpenTelemetry), SLO-based alerts.

## Overview

### Architecture and Key Components

- FastAPI application:
  - Routes:
    - /auth (password flow: register/login/logout/refresh/me)
    - /oauth/google, /oauth/twitter (OAuth 2.0, PKCE + state)
    - /api/products (CRUD, roles: seller/admin)
    - HTML UI (login/register/dashboard), UiAuthRedirect middleware
    - /health (liveness/readiness)
  - Middleware:
    - CORS
    - UiAuthRedirect (for server-side HTML paths)
- Service layer:
  - services/auth_service.py, services/oauth_*_service.py, services/products_service.py
  - Permission checks (seller/admin) and ownership checks (owner) enforced in services
- Data access:
  - asyncpg pool, db/*_db.py
  - Tables: users, user_identities, sessions, products
  - Sessions (refresh) stored in sessions table (hash + TTL + revoke)
- Configuration:
  - config.py reads .env/environment variables; supports DATABASE_URL or assembling from DB_*
  - Important flags: APPLY_SCHEMA_ON_START, COOKIE_SECURE, CORS_ORIGINS, OAuth settings
- Schema initialization:
  - install/schema.sql applied at startup (when APPLY_SCHEMA_ON_START=true)
  - Race protection with multiple workers via advisory lock
- Deployment:
  - Dockerfile + docker-compose.yml (app, db, profiles for init scripts)
  - systemd unit for standalone
  - Admin bootstrap: separate script (one-off command)

### Data Model (brief)

- users: id, email (unique), password_hash, name, avatar_url, role, created_at/updated_at
- user_identities: external OAuth identities (provider, subject), profile
- sessions: refresh sessions (hash, UA, IP, expires_at, revoked_at)
- products: item (seller_id FK->users, title, price, currency, image_url, timestamps)

Notes:
- OAuth users are created with an empty password_hash (password login is disabled until a password is set).
- Roles: buyer (default), seller, admin.

### Key Design Decisions

- Authentication:
  - JWT access (short-lived), refresh via HttpOnly cookie.
  - Refresh cookie: HttpOnly, SameSite=Lax (for redirects), Secure=true in production; name and domain configurable.
  - Passwords: bcrypt (configurable rounds).
- OAuth 2.0:
  - Google: standard auth/token/userinfo.
  - Twitter: OAuth 2.0 + PKCE + state. Important: Twitter does not support multiple callbacks for a single app; a separate app and client_id/secret are used for local development.
  - PKCE: code_verifier stored in a short-lived HttpOnly cookie; state also a cookie.
- Authorization:
  - Role checks and resource ownership checks performed in service layer (seller/admin; owner-only).
- Database schema application:
  - On startup (via flag) from install/schema.sql.
  - Advisory lock prevents race conditions across multiple uvicorn workers.
- Logging:
  - Single logger, info events for key operations; plan: JSON format and correlation.

### 5. Security Compliance

Below is a mapping of measures to typical requirements (reference: OWASP ASVS L2 and SOC2/ISO27001 practices at the app level).

- Session and token management:
  - Access token (JWT) expires in about 15 minutes (configurable).
  - Refresh token stored only in a cookie; only its hash is stored in DB (resilient if DB is compromised).
  - Logout/revocation: delete/mark refresh session; "logout all" invalidates all user refresh sessions.
- Passwords:
  - bcrypt (configurable rounds, default 12).
  - Password login is not allowed for OAuth accounts until an explicit password is set (password_hash="").
- Cookies:
  - HttpOnly, SameSite=Lax, Secure=true in production.
  - Cookie Domain not set by default (host-only); configurable if needed.
- CSRF:
  - For HTML forms use a hidden token with CSRF_SECRET; for API prefer Bearer for state-changing requests.
- CORS:
  - DEV allows "*"; PROD explicit whitelist of domains.
- Input validation:
  - Pydantic schemas at API layer; business logic checks in services (e.g., price >= 0).
- Authorization:
  - Roles buyer/seller/admin; ownership checks (seller_id).
- Secrets:
  - Through env/.env (in Docker env_file); distinct client_id/secret for DEV and PROD.
  - Rotation via updating variables and restart.
- Transport security:
  - TLS terminated by reverse proxy (Nginx/Caddy) in front of the app; app listens on 0.0.0.0:8010.
- Brute-force/abuse protection (plan):
  - Rate limiting on /auth/login (Nginx or fastapi-limiter).
  - CAPTCHA/lockout after N failures (planned).
- Logs and PII:
  - Do not log tokens/passwords/codes; redact sensitive headers.
  - Audit events: login/logout, session management, product operations.
- Dependencies and image:
  - Regularly update dependencies; enable SCA (pip-audit, safety).
  - Minimal base image python:3.11-slim; no dev tools in runtime.
- Backups/DR:
  - Backup Postgres volume (pg_dump/volume snapshot); schedule, retention, restore testing in ops procedures.
- Privacy:
  - Minimize PII (email required; name/avatar optional).
  - GDPR: deletion requests cascade to user_identities, sessions, products (ON DELETE CASCADE).

Potential Challenges and Solutions:
- Twitter OAuth single callback per app: use separate apps for PROD and DEV (different client_id/secret).
- Cookie secure/domain in DEV: Secure=false for http://localhost, empty domain (host-only).
- Schema init with multiple workers: advisory lock (pg_advisory_lock/unlock).
- Proxy and client IP: trust only X-Forwarded-For from your reverse proxy; otherwise use request.client.host.

### Deployment, Environments, and Configuration

- Environments: dev, stage, prod; separate credentials (JWT/CSRF secrets, OAuth client_id/secret), databases, and domains.
- Docker Compose:
  - services: db (postgres:16), app (uvicorn), optionally init-admin (one-off).
  - env_file: .env (app), .env.db (db); recommend specifying DATABASE_URL explicitly in .env.
  - Ports: 8010:8010 (dev); in prod behind reverse proxy.
- systemd:
  - oob.service (uvicorn --host 0.0.0.0 --port 8010 --workers N).
  - EnvironmentFile=/var/www/oob/.env; restart and logs via journalctl.
- Admin bootstrap:
  - One of the options:
    - One-off command: `docker compose run --rm app python -m install.docker.create_admin --email ... --password ... --role admin`
    - Or via SQL (psql) with a precomputed bcrypt hash.
- Migrations:
  - Currently schema.sql + advisory lock.
  - Plan Alembic for versioned migrations.
Below is a native installation with separate hosting. Next also the Docker installation steps.



## Install and config

### Base

```bash
cd /var/www
git clone https://github.com/sphynkx/oob
cd oob
cp install/.env-sample .env
```
Modify `.env` with your own params.

Go to [Google Cloud Console](https://console.cloud.google.com/), create new Web-app, config it, get secrets, set them to `.env` also.

Go to [Twiter Dev Portal](https://developer.x.com/en/portal/petition/essential/basic-info), create new Web-app, config it, get secrets, set them to `.env` also.


### DB

Add to `/var/lib/pgsql/data/pg_hba.conf`:
```conf
# oob app
local   oob01           oob                             scram-sha-256
host    oob01           oob        127.0.0.1/32         scram-sha-256
host    oob01           oob        ::1/128              scram-sha-256
```
Replace 'ADMIN_PASSWORD' to postgres admin password and 'SECRET' to the same as in the `.env`. And run:
```bash
sudo -u postgres PGPASSWORD='ADMIN_PASSWORD'  psql -v db_user='oob' -v db_name='oob01' -v db_pass='SECRET' -f install/prep.sql
sudo -u postgres psql -d oob01  -f install/schema.sql
service postgresql restart
```


### Nginx

On external hosting server - create `/etc/nginx/conf.d/oob.conf`:
```conf
server {
        server_name  oob.sphynkx.org.ua;
        listen       80;
        access_log   /var/log/nginx/oob-access.log  main;
        error_log   /var/log/nginx/oob-error.log;
        location / {
        proxy_pass      http://192.168.7.3:8010;
        proxy_connect_timeout       600;
        proxy_send_timeout          600;
        proxy_read_timeout          600;
        send_timeout                600;
        }
}
```
Then:
```bash
service nginx restart
letsencrypt
```
Choose subdomain and set option __2__. 


### App start

```bash
chmod a+x run.sh
./run.sh
```
After first run comment out "pip install .." lines.

Check on server side (set your creds):
```bash
curl https://oob.sphynkx.org.ua/health
ACCESS_TOKEN=$(curl -s -X POST https://oob.sphynkx.org.ua/auth/login -H "Content-Type: application/json" -c cookies.txt -d '{"email":"no@thankx.com","password":"Reendav8"}' | jq -r .access_token); echo "$ACCESS_TOKEN"
curl -s https://oob.sphynkx.org.ua/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
curl -s https://oob.sphynkx.org.ua/api/products -H "Authorization: Bearer $ACCESS_TOKEN" | jq
curl -s https://oob.sphynkx.org.ua/api/products/6 -H "Authorization: Bearer $ACCESS_TOKEN" | jq
```


### Systemd

If everything is OK configure service:
```bash
cp install/systemd/oob.service /etc/systemd/system/oob.service
systemctl daemon-reload
systemctl enable oob.service
systemctl start oob.service
```


## Docker install

### Preconfig

Copy sample files:
```bash
cp install/docker/.env-sample install/docker/.env
cp install/docker/.env.db-sample install/docker/.env.db
```
and set all necessary values (JWT_SECRET, POSTGRES_PASSWORD, etc.)

For login via social network accounts you need to go to Dev portals, create separate apps for docker installation - same as described above. Receive tokens and keys, set them to `install/docker/.env`

For initial local admin user set your credits into `ADMIN_EMAIL` and `ADMIN_PASSWORD` params.


### Build and run

Build images and start containers, create admin user for local auth.:
```bash
cd install/docker
docker compose -f docker-compose.yml up -d --build
docker compose run --rm -it app python -m install.docker.create_admin
```
Check users and logs:
```bash
docker compose exec -T db psql -U oob -d oob01 -c "SELECT * FROM users;"
docker compose -f install/docker/docker-compose.yml logs -f app
docker compose -f install/docker/docker-compose.yml logs -f db
```
Requests (cmd version, set your creds):
```
for /f "delims=" %A in ('curl -s -X POST http://localhost:8010/auth/login -H "Content-Type: application/json" -c cookies.txt -d "{\"email\":\"E@MAIL\",\"password\":\"PASSWORD\"}" ^| jq -r .access_token') do set ACCESS_TOKEN=%A
curl -s http://localhost:8010/auth/me -H "Authorization: Bearer $ACCESS_TOKEN"
curl -s http://localhost:8010/api/products -H "Authorization: Bearer %ACCESS_TOKEN%" | jq
curl -s http://localhost:8010/api/products/1 -H "Authorization: Bearer %ACCESS_TOKEN%" | jq

```


### Access

http://localhost:8010
