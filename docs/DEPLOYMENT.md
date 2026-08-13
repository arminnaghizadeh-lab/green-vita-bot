# DEPLOYMENT — Green Vita AI Plant Clinic

## متغیرهای محیطی (`.env.example`)

| گروه | متغیر | پیش‌فرض | الزامی؟ |
|---|---|---|---|
| App | `APP_ENV` | `development` | خیر |
| App | `APP_NAME` | `"Green Vita AI Plant Clinic"` | خیر |
| App | `DEBUG` | `true` | خیر |
| App | `SECRET_KEY` | مقدار ناامن پیش‌فرض | ⚠️ باید در production عوض شود (فعلاً هیچ‌جا مصرف نمی‌شود) |
| App | `TIMEZONE` | `Asia/Tehran` | خیر (فعلاً در هیچ کدی خوانده نمی‌شود) |
| Telegram | `BOT_TOKEN` | — | **بله** (نبود آن باعث crash عمدی بات می‌شود) |
| Telegram | `BOT_ADMIN_IDS` | — | برای اطلاع‌رسانی «درخواست ویزیت» و `scripts/seed.py` |
| DB | `DATABASE_URL` | postgres async URL نمونه | **بله** (خالی باشد یعنی SQLite لوکال) |
| DB | `POSTGRES_*` | — | فقط برای docker-compose (ساخت کانتینر Postgres) |
| Redis | `REDIS_URL` | `redis://redis:6379/0` | برای FSM storage بات |
| AI | `AI_PROVIDER` | `claude` | **بله** — یکی از `claude`/`gemini`/`openai` |
| AI | `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — / `claude-sonnet-4-6` | اگر `AI_PROVIDER=claude` |
| AI | `GEMINI_API_KEY` / `GEMINI_MODEL` | — / `gemini-2.0-flash` | اگر `AI_PROVIDER=gemini` |
| AI | `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-4o` | اگر `AI_PROVIDER=openai` |
| Admin | `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_SESSION_SECRET` | — | ⚠️ تعریف‌شده ولی فعلاً مصرف نمی‌شوند (`ADMIN_PANEL.md`) |
| Admin | `ADMIN_PORT` | `8000` | خیر (پورت واقعی از `PORT` در Dockerfile.admin می‌آید) |
| Logging | `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `json` | خیر |

خواندن همه از طریق `src/core/config.py::Settings` (pydantic-settings)، کش‌شده با
`get_settings()`.

## Docker

دو Dockerfile مستقل (چون دو سرویس مستقل هستند):

### `docker/Dockerfile.bot`
- بیس: `python:3.12-slim`
- نصب `build-essential`, `libpq-dev` (برای build کردن `asyncpg`)
- `pip install -r requirements.txt`
- کپی `src/`, `alembic/`, `alembic.ini`, `scripts/`
- اجرا با کاربر غیر-روت (`appuser`)
- `CMD ["python", "-m", "src.bot.main"]`
- **هیچ پورتی expose نمی‌کند** (بات هیچ HTTP server ندارد — به `KNOWN_ISSUES.md` نگاه کنید)

### `docker/Dockerfile.admin`
- همان بیس و مراحل نصب
- `ENV PORT=8000`, `EXPOSE 8000`
- `CMD exec uvicorn src.admin.main:app --host 0.0.0.0 --port ${PORT}`

هر دو Dockerfile تک‌مرحله‌ای هستند (بدون multi-stage build).

## docker-compose.yml

سرویس‌ها:

| سرویس | ایمیج/Build | نقش |
|---|---|---|
| `db` | `postgres:16-alpine` | دیتابیس، با healthcheck (`pg_isready`) |
| `redis` | `redis:7-alpine` | FSM storage، با healthcheck (`redis-cli ping`) |
| `migrate` | `Dockerfile.bot` | یک‌بار اجرا: `alembic upgrade head`، منتظر `db` سالم |
| `bot` | `Dockerfile.bot` | منتظر `db`+`redis` سالم و `migrate` موفق |
| `admin` | `Dockerfile.admin` | منتظر همان‌ها، پورت `8000` باز، healthcheck روی `/health` |

اجرا: `docker compose up -d --build` یا `make docker-up`.

## Cloud Run (`cloudrun/*.yaml`)

### `bot-service.yaml`
- `minScale=1`, `maxScale=1` (چون بات polling است و نباید چند نمونه هم‌زمان اجرا شود)
- `containerConcurrency: 1`, `timeoutSeconds: 3600`
- `cpu-throttling: "false"` (CPU همیشه فعال، نه فقط حین پردازش request)
- Secretها از Secret Manager: `BOT_TOKEN`, `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`
- ⚠️ **این سرویس هیچ پورتی expose نمی‌کند و هیچ HTTP endpoint ای ندارد** — ناسازگاری مهم با
  مدل `Service` در Cloud Run (به `KNOWN_ISSUES.md` نگاه کنید، اولویت Critical)

### `admin-service.yaml`
- `minScale=0`, `maxScale=3` (scale-to-zero مجاز)
- `containerConcurrency: 40`, `timeoutSeconds: 60`
- Secretها: `DATABASE_URL`, `REDIS_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET`
  (هرچند فعلاً در کد استفاده نمی‌شوند)

دیپلوی دستی:
```bash
gcloud run services replace cloudrun/bot-service.yaml --region <REGION>
gcloud run services replace cloudrun/admin-service.yaml --region <REGION>
```

## CI/CD (`.github/workflows/ci-cd.yml`)

دو job:

1. **`lint-and-test`** (روی هر push/PR به `main`):
   - سرویس Postgres موقت برای تست
   - `ruff check`, `mypy` (`continue-on-error: true` — یعنی فعلاً fail نمی‌کند)
   - `pytest --cov=src` با `DATABASE_URL=sqlite+aiosqlite:///:memory:`
   - آپلود گزارش پوشش کد به‌عنوان artifact

2. **`build-and-push`** (فقط روی push مستقیم به `main`، بعد از موفقیت job اول):
   - احراز هویت با Workload Identity Federation (`google-github-actions/auth`)
   - build و push دو ایمیج (`bot`, `admin`) به Artifact Registry با تگ `latest` + SHA کامیت
   - `gcloud run deploy` مستقیم برای هر دو سرویس (بدون مرحله‌ی staging/تأیید دستی)

Secretهای موردنیاز در GitHub: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`,
`GCP_PROJECT_ID`, `GCP_REGION`.

## Makefile (خلاصه دستورات)

| دستور | کار |
|---|---|
| `make install` / `make dev-install` | نصب وابستگی‌ها |
| `make run-bot` / `make run-admin` | اجرای لوکال (بدون Docker) |
| `make migrate` / `make migrate-new m="..."` | مایگریشن |
| `make seed` | اجرای `scripts/seed.py` |
| `make test` / `make lint` / `make format` | تست و کیفیت کد |
| `make docker-up` / `make docker-down` / `make docker-build` / `make docker-logs` | مدیریت docker-compose |

## ترتیب پیشنهادی راه‌اندازی از صفر

```bash
cp .env.example .env          # و پر کردن مقادیر واقعی
make docker-up                # یا: docker compose up -d --build
docker compose run --rm migrate   # (اتوماتیک هم اجرا می‌شود ولی برای اطمینان)
docker compose run --rm bot python -m scripts.seed
```
