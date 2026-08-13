# MVP_DEPLOYMENT_VERIFICATION — Green Vita v0.1

> بررسی استاتیک روی ریپازیتوری واقعی (آخرین commit: `6fe34a8`). هیچ فایلی تغییر نکرده،
> هیچ commit ای انجام نشده. چون محیط تولید این گزارش به شبکه/Docker دسترسی ندارد، این
> بررسی از طریق خواندن دقیق فایل‌ها انجام شده، نه اجرای واقعی کانتینرها.

---

## ۱. `docker-compose.yml`

| بررسی | نتیجه |
|---|---|
| همه‌ی فایل‌های ارجاع‌شده وجود دارند؟ | ✅ `docker/Dockerfile.bot`, `docker/Dockerfile.admin`, `.env` (باید خودت بسازی از `.env.example`) |
| نام سرویس‌ها با hostnameهای داخلی هماهنگ‌اند؟ | ✅ `DATABASE_URL` پیش‌فرض از `db:5432` استفاده می‌کند (= نام سرویس `db`)؛ `REDIS_URL` از `redis:6379` (= نام سرویس `redis`) |
| شرط‌های `depends_on` معتبرند؟ | ✅ `migrate` منتظر `db: service_healthy`؛ `bot`/`admin` منتظر `db: healthy` + `redis: healthy` + `migrate: service_completed_successfully` — دقیقاً ترتیب درست |
| healthcheckها معتبرند؟ | ✅ `db`: `pg_isready` (داخل ایمیج `postgres:16-alpine` موجود است) / ✅ `redis`: `redis-cli ping` (داخل ایمیج `redis:7-alpine` موجود است) / ✅ `admin`: `python -c "urllib.request..."` روی `/health` (بدون auth، کار می‌کند) / ⚠️ **`bot` هیچ healthcheck ندارد** (پایین توضیح داده شده) |
| Restart policyها مناسب‌اند؟ | ✅ `db`/`redis`/`bot`/`admin`: `unless-stopped` (درست) / ✅ `migrate`: بدون restart policy (درست — یک job یک‌بارمصرف نباید restart-loop بگیرد) |

**یافته‌ها:**
- 🟡 سرویس `bot` هیچ `healthcheck` ندارد. چون `restart: unless-stopped` هست، اگر پروسه واقعاً کرش کند Docker خودش دوباره بالا می‌آورد؛ ولی اگر پروسه هنگ کند (بدون crash)، هیچ مکانیزمی برای تشخیص/ری‌استارت خودکار آن نیست.
- 🟠 پورت‌های `db` (`5432`) و `redis` (`6379`) با `ports:` (نه فقط شبکه‌ی داخلی Compose) منتشر می‌شوند — یعنی روی رابط `0.0.0.0` سرور باز می‌شوند. **Redis هیچ authentication ای در کل پروژه ندارد** (نه در `docker-compose.yml`، نه در `Settings`). اگر فایروال سرور این دو پورت را نبندد، دیتابیس و Redis از اینترنت عمومی در دسترس خواهند بود.

---

## ۲. `docker/Dockerfile.bot`

| بررسی | نتیجه |
|---|---|
| `WORKDIR` درست است؟ | ✅ `/app` — با مسیرهای نسبی استفاده‌شده در کد (`alembic.ini` → `script_location = alembic`) هماهنگ است |
| مسیر Python درست است؟ | ✅ بیس `python:3.12-slim`، بدون virtualenv اضافه (نیازی هم نیست، تصویر ایزوله است) |
| دستور استارت درست است؟ | ✅ `CMD ["python", "-m", "src.bot.main"]` — منطبق با `src/bot/main.py::if __name__ == "__main__"` |
| همه‌ی فایل‌های لازم کپی می‌شوند؟ | ✅ `requirements.txt`, `src/`, `alembic/`, `alembic.ini`, `scripts/` — همه‌چیزی که `python -m src.bot.main` و `alembic upgrade head` لازم دارند |
| وابستگی‌ها در دسترس‌اند؟ | ✅ `pip install -r requirements.txt` قبل از کپی کد اجرا می‌شود (cache-friendly)؛ همه‌ی importهای پروژه در `requirements.txt` هستند (تأیید شده در بخش ۶) |

**یافته‌ای که بلاک‌کننده نیست ولی قابل‌ذکر است:** بعد از `USER appuser`، اگر کسی `DATABASE_URL` را به SQLite تغییر دهد (فقط برای dev لوکال، نه مسیر پیشنهادی این MVP)، `appuser` روی دایرکتوری `/app` (مالک `root`) اجازه‌ی نوشتن فایل دیتابیس را ندارد. **این روی مسیر Postgres (که در `docker-compose.yml` استفاده می‌شود) هیچ اثری ندارد.**

---

## ۳. `docker/Dockerfile.admin`

همان بررسی‌های بالا، به‌علاوه:

| بررسی | نتیجه |
|---|---|
| دستور استارت و پورت | ✅ `CMD exec uvicorn src.admin.main:app --host 0.0.0.0 --port ${PORT}` با `ENV PORT=8000` و `EXPOSE 8000` — منطبق با `ports: ["8000:8000"]` در compose |
| مسیرهای نسبی static/templates | ✅ `src/admin/main.py` از `"src/admin/static"` و `"src/admin/templates"` استفاده می‌کند — چون `WORKDIR /app` و `COPY src ./src`، این مسیرها در `/app/src/admin/...` درست resolve می‌شوند؛ هر دو پوشه واقعاً وجود دارند و در تصویر کپی می‌شوند |

بدون یافته‌ی جدید.

---

## ۴. دیتابیس

| بررسی | نتیجه |
|---|---|
| کانفیگ سرویس Postgres | ✅ `postgres:16-alpine`، env از `${POSTGRES_USER/PASSWORD/DB}` (خوانده از `.env` توسط خودِ Docker Compose، مکانیزم استاندارد) |
| `DATABASE_URL` | ✅ در `src/core/config.py` با یک `field_validator` نرمال‌سازی می‌شود (`postgres://`/`postgresql://` → `postgresql+asyncpg://`)؛ پیش‌فرض `.env.example` از قبل با پیشوند درست است |
| کانفیگ Alembic | ✅ `alembic/env.py` مستقیم از `get_settings().database_url` می‌خواند (نه یک URL جدا در `alembic.ini`) — یک منبع حقیقت واحد، امکان ناهماهنگی بین بات و مایگریشن وجود ندارد |
| سرویس migrate | ✅ `alembic upgrade head` را اجرا و خارج می‌شود؛ `bot`/`admin` منتظر موفقیت کاملش می‌مانند |
| ترتیب مایگریشن‌ها | ✅ ۵ فایل، زنجیره‌ی خطی و بدون شکاف: `0001→0002→0003→0004→0005` (بررسی مستقیم `revision`/`down_revision` هر فایل) |
| وابستگی استارت بات/پنل به مایگریشن | ✅ `condition: service_completed_successfully` — بات/پنل تا مایگریشن موفق کامل نشود اصلاً بالا نمی‌آیند |

بدون یافته‌ی جدید (این بخش کاملاً سالم است).

---

## ۵. Redis

| بررسی | نتیجه |
|---|---|
| `REDIS_URL` | ✅ پیش‌فرض `.env.example`: `redis://redis:6379/0` — با نام سرویس هماهنگ |
| مقداردهی `RedisStorage` | ⚠️ `src/bot/main.py::_build_storage` با `try/except` دور `RedisStorage.from_url()` پیاده شده، ولی `from_url()` فقط یک کلاینت می‌سازد و **اتصال واقعی برقرار نمی‌کند** — یعنی اگر Redis واقعاً پایین باشد، این `except` عملاً هیچ‌وقت trigger نمی‌شود و خطا اولین بار وسط یک مکالمه‌ی کاربر (نه در startup) ظاهر می‌شود |
| Hostname سرویس | ✅ `redis` — با نام سرویس در compose هماهنگ |
| Persistence/Restart | ⚠️ سرویس `redis` هیچ volume ای ندارد (پایین، بخش ۱۰) — با هر بار recreate شدن کانتینر، تمام state مکالمه‌های در حال انجام (نه دیتای دائمی) پاک می‌شود |

**نکته‌ی مهم برای این بررسی:** این رفتار **مانع استارت امن بات نمی‌شود** — بات با Redis پایین هم بالا می‌آید و کار می‌کند (فقط وسط یک مکالمه‌ی خاص خطا می‌دهد)، پس طبق تعریف این وظیفه بلاک‌کننده نیست، ولی برای پایداری واقعی مهم است.

---

## ۶. متغیرهای محیطی

مقایسه‌ی خودکار بین فیلدهای `Settings` (`src/core/config.py`) و `.env.example`:

```
Settings fields NOT in .env.example: []
Vars in .env.example NOT in Settings: []
Total: 28 / 28 — تطبیق کامل
```

مقایسه‌ی importهای شخص‌ثالث استفاده‌شده در `src/` با `requirements.txt`: همه‌ی importهای واقعی
کد (`aiogram`, `anthropic`, `fastapi`, `google.generativeai`, `openai`, `pydantic`,
`pydantic_settings`, `sqlalchemy`, `structlog`, `tenacity`) در `requirements.txt` حاضرند؛
`jinja2` هم برای `Jinja2Templates` لازم است و هست؛ `redis` هم برای `RedisStorage` لازم است و
هست. **چیزی کم یا اضافه نیست.**

بدون یافته‌ی جدید.

---

## ۷. استارت بات

| بررسی | نتیجه |
|---|---|
| `python -m src.bot.main` معتبر است؟ | ✅ `src/bot/main.py` دارای `if __name__ == "__main__": main()` است و `main()` واقعاً `run_bot()` را با `asyncio.run` اجرا می‌کند |
| importهای لازم در استارت | ✅ همه‌ی importهای بالای فایل (`aiogram`, `src.ai.factory`, `src.bot.handlers`, `src.bot.middlewares`, `src.core.config`, `src.core.exceptions`, `src.core.logging`) در `requirements.txt`/کد پروژه موجودند؛ `py_compile` روی کل پروژه بدون خطا |
| مسیر استارت polling | ✅ ترتیب صحیح: چک `BOT_TOKEN` → چک `get_ai_provider()` (اصلاح v0.1-baseline) → ساخت `Bot`/`Dispatcher` → `delete_webhook(drop_pending_updates=True)` → `start_polling(bot)` |

بدون یافته‌ی جدید (این بخش در `v0.1-baseline` قبلاً سخت شده بود).

---

## ۸. استارت پنل مدیریت

| بررسی | نتیجه |
|---|---|
| دستور و پورت | ✅ بخش ۳ را ببین |
| health endpointها | ✅ `GET /health` (liveness ساده) و `GET /health/ready` (چک واقعی دیتابیس با `SELECT 1`) هر دو در `src/admin/routers/health.py` تعریف و در `get_root_router()` ثبت شده‌اند |

**یافته‌ی از قبل مستندشده (نه جدید):** `/health/ready` حتی وقتی `database` خطا برگرداند، همچنان
HTTP status ۲۰۰ می‌دهد (وضعیت فقط در بدنه‌ی JSON است) — برای مانیتورینگ خودکار مبتنی بر
status code گمراه‌کننده است، ولی **مانع استارت پنل نمی‌شود.**

---

## ۹. پروایدر هوش مصنوعی

هر سه پروایدر بررسی شد — سازنده‌ی هرکدام کاملاً local است (فقط ساخت کلاینت SDK، بدون
فراخوانی شبکه‌ای در `__init__`)، یعنی `get_ai_provider()` در استارت بات فقط "خالی نبودن
کلید" را تست می‌کند، نه اعتبار واقعی کلید:

| پروایدر | سازنده | مشکل احتمالی دیپلوی |
|---|---|---|
| `ClaudeProvider` | `AsyncAnthropic(api_key=...)` | هیچ (مسیر رسمی) |
| `GeminiProvider` | `genai.configure(api_key=...)` | هیچ (مسیر رسمی) |
| `OpenAIProvider` | `AsyncOpenAI(api_key=..., base_url=...)` | **مسیر انتخابی این پروژه فعلاً همین است** (`AI_PROVIDER=openai` + `OPENAI_BASE_URL=https://api.avalai.ir/v1` برای دسترسی به Claude از طریق AvalAI) — از نظر کد کاملاً معتبر و تست‌شده (`tests/test_ai_factory.py`) |

**یافته (غیربلاک‌کننده، فقط برای آگاهی):** چون سازنده‌ها کلید را از نظر شبکه‌ای تست نمی‌کنند،
یک کلید API **غلط ولی غیرخالی** (مثلاً تایپی یا منقضی) بات را از استارت متوقف نمی‌کند —
فقط اولین درخواست واقعی کاربر با `AIProviderError` شکست می‌خورد. توصیه: بعد از دیپلوی،
تست دود واقعی (بخش ۹ چک‌لیست قبلی) را حتماً انجام بده تا از اعتبار واقعی کلید مطمئن شوی.

---

## ۱۰. دیتای پایدار (Persistent Data)

| Volume | سرویس | چه چیزی نگه می‌دارد | با recreate شدن کانتینر چه می‌شود؟ |
|---|---|---|---|
| `pgdata` | `db` | تمام جدول‌های Postgres (کاربران، تشخیص‌ها، شناسایی‌ها، ...) | ✅ باقی می‌ماند (volume جدا از عمر کانتینر است) |
| **(هیچ‌کدام)** | `redis` | فقط state موقت FSM (مثلاً «کاربر منتظر پاسخ سوال اسم گیاه») | ⚠️ **از بین می‌رود** — کاربرانی که وسط یک مکالمه‌ی چندمرحله‌ای (تشخیص بیماری/شناسایی گیاه) هستند باید از اول عکس بفرستند |

نکته‌ی مهم: **هیچ دیتای دائمی/کسب‌وکاری (تشخیص، کاربر، شناسایی گیاه) در Redis ذخیره
نمی‌شود** — همه‌ی این‌ها در Postgres (با volume پایدار) هستند. از دست رفتن Redis فقط یعنی
از سرگرفتن یک مکالمه‌ی نیمه‌کاره، نه از دست رفتن دیتای واقعی.

---

## ۱۱. طبقه‌بندی بلاک‌کننده‌های واقعی

طبق تعریف این وظیفه (فقط چیزی که مانع استارت امن می‌شود، نه فیچرهای آینده):

### 🔴 Critical
**هیچ‌کدام.**

### 🟠 High
1. **پورت‌های Postgres (`5432`) و Redis (`6379`) بدون هیچ authentication روی Redis، به‌صورت پیش‌فرض روی تمام رابط‌های شبکه‌ی سرور منتشر می‌شوند.**
   فایل مسئول: `docker-compose.yml` (بخش `ports:` در سرویس‌های `db` و `redis`)
   این مانع «استارت» نمی‌شود ولی اگر فایروال سرور این دو پورت را نبندد، دیتابیس و Redis
   از اینترنت عمومی قابل‌دسترسی خواهند بود. **اقدام لازم: قبل از باز کردن سرور به اینترنت،
   فقط پورت‌های `22` و `8000` (و آن هم محدود) را در فایروال باز نگه دار؛ `5432`/`6379` را
   عمومی باز نگذار.** (این نکته باید به `MVP_DEPLOYMENT_PLAN.md` هم اضافه شود — پیشنهاد،
   نه انجام‌شده در این بررسی چون قرار نبود فایلی تغییر کند.)

### 🟡 Medium
2. **Fallback به `MemoryStorage` عملاً هیچ‌وقت trigger نمی‌شود چون `RedisStorage.from_url()` اتصال واقعی تست نمی‌کند.**
   فایل مسئول: `src/bot/main.py`
   قطعی Redis فقط وسط یک مکالمه‌ی کاربر خودش را نشان می‌دهد، نه در لاگ استارت. غیربلاک‌کننده.
3. **سرویس `bot` هیچ Docker healthcheck ندارد.**
   فایل مسئول: `docker-compose.yml`
   اگر پروسه بدون crash هنگ کند، هیچ مکانیزم خودکاری آن را تشخیص/ری‌استارت نمی‌کند.

### 🟢 Low
4. **کلید API نامعتبر (نه خالی) در استارت بات تشخیص داده نمی‌شود.**
   فایل مسئول: `src/ai/providers/*.py` (طراحی SDKها، نه باگ پروژه)
   فقط با تست دود واقعی بعد از دیپلوی قابل‌کشف است.
5. **Redis بدون volume — از دست رفتن state موقت مکالمه با recreate شدن کانتینر.**
   فایل مسئول: `docker-compose.yml`
   فقط تجربه‌ی کاربری («از اول شروع کن») را تحت تأثیر قرار می‌دهد، نه دیتای دائمی.
6. **`/health/ready` همیشه HTTP 200 برمی‌گرداند حتی وقتی دیتابیس down باشد.**
   فایل مسئول: `src/admin/routers/health.py`
   قبلاً در `docs/KNOWN_ISSUES.md` (مورد H4) مستند شده — تکرار نشد به‌عنوان یافته‌ی جدید.

---

## نتیجه‌ی نهایی

هیچ مشکلی که «استارت امن» بات یا پنل مدیریت را در معماری polling فعلی مسدود کند پیدا نشد.
تنها مورد High (پورت‌های باز Postgres/Redis) یک ریسک امنیتی زیرساختی است که با تنظیم
فایروال روی سرور (نه تغییر کد) قابل‌رفع است — دقیقاً همان کاری که `MVP_DEPLOYMENT_PLAN.md`
از قبل برای پورت پنل مدیریت توصیه کرده بود؛ باید همان توصیه برای `5432`/`6379` هم تکرار شود.

# MVP DEPLOYMENT STATUS: READY
