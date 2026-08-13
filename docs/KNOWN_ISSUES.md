# KNOWN_ISSUES — Green Vita AI Plant Clinic

این فایل بدهی‌های فنی و ریسک‌های شناخته‌شده‌ی کد فعلی را مستند می‌کند — بر اساس بررسی کامل
کد، بدون هیچ فرض یا حدس. اولویت‌بندی بر اساس تأثیر روی پروداکشن است، نه ترتیب کشف.

---

## 🔴 Critical

### C1. پنل مدیریت کاملاً بدون احراز هویت است
`src/admin/main.py` و `src/admin/routers/dashboard.py` هیچ لایه‌ی login/session/API-key
ندارند. هرکسی که URL پنل را داشته باشد به داشبورد دسترسی دارد. تنظیمات `admin_username`,
`admin_password`, `admin_session_secret` در `src/core/config.py` تعریف شده‌اند ولی **در هیچ
فایلی import/استفاده نمی‌شوند** (تأییدشده با جستجوی کامل کد).
**ریسک:** افشای آمار داخلی به هر کسی؛ اگر در آینده داده‌ی حساس‌تر (اطلاعات تماس کاربران،
تشخیص‌ها) به پنل اضافه شود، این ریسک به افشای داده تبدیل می‌شود.

### C2. سرویس بات روی Cloud Run هیچ HTTP endpoint ندارد ولی به‌عنوان Knative `Service` تعریف شده
`docker/Dockerfile.bot` هیچ پورتی expose نمی‌کند و بات فقط با long-polling کار می‌کند.
`cloudrun/bot-service.yaml` اما `kind: Service` است — این نوع منبع در Cloud Run انتظار دارد
کانتینر روی `$PORT` به HTTP گوش بدهد؛ بدون آن، احتمال شکست startup probe و ناتوانی در
deploy موفق وجود دارد.
**راه‌حل‌های ممکن (برای فاز بعد):** یک HTTP server سبک (health endpoint) داخل پروسه‌ی بات
اضافه شود، یا از Cloud Run Jobs/GCE/یک VM ساده به‌جای Knative Service استفاده شود، یا بات
به حالت webhook (که خودش یک FastAPI endpoint است) مهاجرت کند.

### C3. مقادیر پیش‌فرض ناامن برای Secretها، بدون validation در production
`SECRET_KEY = "insecure-dev-key-change-me"`، `ADMIN_PASSWORD = "admin"`،
`ADMIN_SESSION_SECRET = "insecure-session-secret-change-me"` (`src/core/config.py`).
هیچ‌جا چک نمی‌شود که در `APP_ENV=production` این مقادیر عوض شده باشند — اگر کسی فراموش
کند مقدار واقعی در `.env` بگذارد، سرویس با مقدار ناامن پیش‌فرض بالا می‌آید، بدون هیچ هشدار
یا خطا.

---

## 🟠 High

### H1. هیچ Rate Limiting/Throttling روی هندلرهای بات نیست
هر کاربر می‌تواند بی‌نهایت عکس پشت‌سرهم بفرستد و هر کدام یک فراخوانی پولی به Claude/Gemini/
OpenAI بزند. هیچ محدودیت per-user یا per-IP (در سطح بات، per-user) وجود ندارد.
**ریسک:** هزینه‌ی کنترل‌نشده‌ی API + امکان سوءاستفاده (spam/DoS ساده روی بودجه‌ی AI).

### H2. منطق fallback به MemoryStorage برای FSM عملاً کار نمی‌کند
`src/bot/main.py::_build_storage`:
```python
try:
    return RedisStorage.from_url(settings.redis_url)
except Exception:
    return MemoryStorage()
```
`RedisStorage.from_url()` فقط یک آبجکت کلاینت می‌سازد و **اتصال واقعی برقرار نمی‌کند** —
پس این `except` عملاً هیچ‌وقت trigger نمی‌شود. اگر Redis واقعاً در دسترس نباشد، خطا اولین
بار وسط یک مکالمه (هنگام `state.set_state`/`state.get_data`) به‌صورت استثنای مدیریت‌نشده
رخ می‌دهد، نه در استارتاپ.

### H3. هیچ Global Error Handler برای aiogram Dispatcher ثبت نشده
هیچ `@dp.error()` یا مشابه آن وجود ندارد. برای هندلرهایی که خودشان try/except ندارند
(`start.py`, `help.py`, `about.py`) یک استثنای مدیریت‌نشده فقط لاگ می‌شود
(`LoggingMiddleware`) و کاربر **هیچ پاسخی دریافت نمی‌کند** — تجربه‌ی کاربری بد در خطاهای
غیرمنتظره (مثلاً دیتابیس موقتاً در دسترس نباشد).

### H4. `/health/ready` همیشه HTTP 200 برمی‌گرداند، حتی وقتی دیتابیس down است
`src/admin/routers/health.py::readiness_check` وضعیت را در بدنه‌ی JSON می‌گذارد
(`"status": "degraded"`) ولی status code همیشه ۲۰۰ است. یک load balancer یا Cloud Run
health check که فقط status code را چک می‌کند، سرویس ناسالم را سالم تشخیص می‌دهد.

### H5. هیچ اعتبارسنجی حجم/نوع فایل روی عکس ورودی نیست
`handlers/diagnosis.py` و `handlers/identification.py` مستقیم `bot.download(file_id)` را
صدا می‌زنند و بایت‌ها را به AI provider می‌فرستند — بدون چک حداکثر سایز یا نوع MIME.
**ریسک:** فایل‌های خیلی بزرگ = هزینه/تأخیر زیاد؛ در تئوری امکان سوءاستفاده.

### H6. اتصال Redis از Cloud Run مستندسازی/زیرساخت ندارد
`cloudrun/*.yaml` مقدار `REDIS_URL` را از Secret Manager می‌خواند ولی هیچ Serverless VPC
Access Connector یا معماری شبکه‌ای برای رسیدن به یک Redis خصوصی (مثل Memorystore) تعریف
نشده. بدون این، یا باید Redis عمومی (ناامن) استفاده شود یا اتصال اصلاً برقرار نمی‌شود.

---

## 🟡 Medium

### M1. مدل‌های `Plant`, `Conversation`, `Reminder` تعریف شده ولی کاملاً بلااستفاده‌اند
هیچ هندلر بات رکوردی از این سه مدل نمی‌سازد یا نمی‌خواند. عدد «تعداد گیاهان» در داشبورد
همیشه ۰ خواهد بود (`ADMIN_PANEL.md`).

### M2. `Diagnosis.plant_id` همیشه `NULL` است؛ `Plant.health_status` هیچ‌وقت آپدیت نمی‌شود
در بازنویسی فاز ۲ (که سؤال «اسم گیاه» جایگزین انتخاب از لیست گیاهان ثبت‌شده شد)، اتصال
`Diagnosis → Plant` قطع شد. جدول `plants` عملاً دیتای واقعی نمی‌گیرد.

### M3. هیچ Timeout صریحی روی کلاینت‌های AI provider تنظیم نشده
`claude_provider.py`, `gemini_provider.py`, `openai_provider.py` هیچ‌کدام `timeout` را به
SDK پاس نمی‌دهند — فقط `tenacity.retry` (۳ تلاش) هست، نه سقف زمانی مشخص برای هر تلاش.

### M4. پوشش تست ناقص
فقط `core/config`, `repositories`, `ai/prompts`+`ai/diagnosis` (پارسر) و `ai/factory` تست
دارند. هیچ تستی برای هندلرهای بات، `ai/plant_identification.py`، یا خودِ providerهای AI
(claude/gemini/openai — حتی با mock) نوشته نشده.

### M5. Dockerfileها تک‌مرحله‌ای هستند (بدون multi-stage build)
`build-essential` و `libpq-dev` در ایمیج نهایی باقی می‌مانند — سایز بزرگ‌تر ایمیج، سطح حمله‌ی
بیشتر، دیپلوی کندتر.

### M6. Base image بدون digest pin
`FROM python:3.12-slim` (تگ متغیر، نه SHA ثابت) — یعنی build بعدی می‌تواند یک ایمیج پایه‌ی
متفاوت (حتی ناسازگار) بگیرد بدون تغییر آگاهانه در کد.

### M7. CI/CD مستقیم به production دیپلوی می‌کند، بدون staging/تأیید دستی
`.github/workflows/ci-cd.yml` هر push موفق به `main` را مستقیم با `gcloud run deploy`
می‌فرستد. هیچ محیط staging یا gate تأیید انسانی نیست.

### M8. مرحله‌ی `mypy` در CI با `continue-on-error: true` است
یعنی خطاهای type-checking هیچ‌وقت pipeline را fail نمی‌کنند — عملاً mypy فقط informational
است، نه enforcement.

### M9. مسیرهای relative برای static/templates در پنل ادمین
`StaticFiles(directory="src/admin/static")` و `Jinja2Templates(directory="src/admin/templates")`
به working directory فرآیند وابسته‌اند؛ در Docker (با `WORKDIR /app`) درست کار می‌کند ولی
اگر کسی از مسیر دیگری اجرا کند می‌شکند.

---

## 🟢 Low

### L1. `TIMEZONE` و `ADMIN_PORT` در `Settings` تعریف شده‌اند ولی هیچ‌جا خوانده نمی‌شوند
کانفیگ مرده — یا باید در کد استفاده شوند یا حذف شوند.

### L2. `User.is_blocked` تعریف شده ولی هیچ هندلری آن را چک نمی‌کند
یعنی مسدودکردن یک کاربر در حال حاضر عملاً هیچ اثری ندارد.

### L3. `User.phone_number` تعریف شده ولی هیچ‌جا پر نمی‌شود
### L4. هیچ `CORSMiddleware` روی FastAPI ثبت نشده (فعلاً چون فرانت‌اند جدا وجود ندارد اولویت پایین است)
### L5. درخواست‌های «ویزیت متخصص» فقط به تلگرام ادمین‌ها فرستاده می‌شوند، در پنل مدیریت هیچ‌جا queryable نیستند
(هرچند `expert_visit_requested` در دیتابیس ذخیره می‌شود، پنل صفحه‌ای برای دیدن آن ندارد)
### L6. هیچ مستند/اسکریپت bootstrap برای زیرساخت اولیه‌ی GCP (Artifact Registry، Secret Manager، Workload Identity) نیست
کاربر باید این‌ها را دستی و بر اساس نام‌های استفاده‌شده در YAML/CI بسازد.

---

## خلاصه‌ی آماری

| اولویت | تعداد مورد |
|---|---|
| 🔴 Critical | 3 |
| 🟠 High | 6 |
| 🟡 Medium | 9 |
| 🟢 Low | 6 |

این فهرست فقط **مشاهده و مستندسازی** است — طبق دستور، هیچ کدی در حین تهیه‌ی این مستندات
تغییر نکرده. رفع هرکدام باید به‌عنوان یک فیچر/فاز جداگانه درخواست و تأیید شود.
