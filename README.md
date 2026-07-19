# Library Hub

Production-oriented Django REST Framework API for a library management system:
catalog (authors, publishers, categories, books), JWT auth with roles, borrow/return,
fines, and staff workflows for lost copies.

## Stack

- Python 3.13+, Django 6, Django REST Framework
- PostgreSQL (development/production), SQLite in-memory (tests)
- SimpleJWT, django-filter, drf-spectacular, WhiteNoise, Gunicorn, Docker

## Project layout

Apps live at the project root (not under `apps/`):

```
library_hub/
├── config/          # settings, urls, wsgi
├── common/          # shared pagination, errors, validators
├── users/           # auth, profiles, admin user management
├── books/           # catalog
├── borrowing/       # loans, fines, overdue/lost
├── manage.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Quick start (local)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # or: cp .env.example .env
# Edit .env: SECRET_KEY, DB_*, EMAIL_*
```

### Database

Use PostgreSQL and set `DJANGO_SETTINGS_MODULE` / your env so development settings load
(`config.settings.development` via project defaults).

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API base: `http://127.0.0.1:8000/api/`  
Docs (dev): `http://127.0.0.1:8000/api/docs/`  
Health: `http://127.0.0.1:8000/health/`

### Tests

```bash
python manage.py test users books borrowing --settings=config.settings.test
```

### Sync overdue statuses (optional cron)

List/retrieve show effective `OVERDUE` without writing. To persist DB status:

```bash
python manage.py sync_overdue
```

## Auth flow

1. `POST /api/auth/register/` → verification email (console backend in development)
2. `GET /api/auth/verify-email/<uid>/<token>/`
3. `POST /api/auth/login/` → `{ access, refresh }`
4. Send `Authorization: Bearer <access>` on protected routes
5. `POST /api/auth/token/refresh/` / `POST /api/auth/logout/`

Roles: `ADMIN`, `LIBRARIAN`, `MEMBER`.

## Main endpoints

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/auth/register/` | Public |
| POST | `/api/auth/login/` | Public |
| CRUD | `/api/books/`, `/api/authors/`, … | Write: staff |
| POST | `/api/borrows/` | Borrow (also `/api/borrows/borrow/`) |
| POST | `/api/borrows/{id}/return/` | Return (also legacy `/api/borrows/return/`) |
| POST | `/api/borrows/{id}/mark-lost/` | Staff |
| POST | `/api/borrows/{id}/resolve-lost/` | Staff; body `{ "restore_inventory": false }` |
| POST | `/api/fines/{id}/pay/` | Staff |

### LOST policy

- Marking lost does **not** restore stock and does **not** count toward borrow limit.
- Same title stays blocked until `resolve-lost`.
- `restore_inventory: true` if the copy was found; otherwise write-off.

## Docker

```bash
# Ensure .env has SECRET_KEY, DB_*, EMAIL_*, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
docker compose up --build
```

Compose waits for Postgres health, runs migrate + collectstatic, then Gunicorn.
Static files are served by WhiteNoise. Media is a named volume.

### Backups

```bash
docker compose exec db pg_dump -U postgres library_hub > backup.sql
```

Schedule `pg_dump` (cron) in production; keep media volume snapshots separately.

### Reverse proxy (optional)

See `deploy/nginx.conf.example` for TLS termination in front of Gunicorn.
Set `SECURE_PROXY_SSL_HEADER` is already enabled in production settings.

## Environment

See `.env.example` for:

- `SECRET_KEY`, `PUBLIC_BASE_URL`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`

Production requires `SECRET_KEY` and uses `config.settings.production` (`DEBUG=False`, HSTS, secure cookies).
