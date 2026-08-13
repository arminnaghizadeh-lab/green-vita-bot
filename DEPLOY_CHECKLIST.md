# DEPLOY_CHECKLIST — Green Vita MVP v0.1

این چک‌لیست برای انتشار اولین نسخه‌ی قابل‌استفاده (MVP v0.1) است. قبل از هر مرحله، مرحله‌ی
قبلی را کامل تیک بزن.

## ۰. خلاصه‌ی وضعیت پروژه (بعد از این ممیزی)

- ✅ سینتکس همه‌ی فایل‌های پایتون بررسی شد (`py_compile`) — تمیز.
- ✅ زنجیره‌ی مایگریشن‌ها بررسی شد (`0001 → 0002 → 0003 → 0004 → 0005`) — خطی و سالم.
- ✅ همه‌ی importهای شخص‌ثالث با `requirements.txt` تطبیق داده شد — چیزی کم نیست.
- ✅ همه‌ی فیلدهای `Settings` (`src/core/config.py`) با `.env.example` یک‌به‌یک تطبیق دارند.
- ✅ ساختار پکیج‌ها (`__init__.py`) در همه‌ی زیرپوشه‌های `src/` کامل است.
- 🔧 **یک تغییر انجام شد:** اعتبارسنجی پیکربندی AI Provider به startup بات اضافه شد (پایین
  را ببین) — تا کانفیگ خراب به‌جای شکست خاموش برای هر کاربر، همان لحظه‌ی دیپلوی مشخص شود.
- ⚠️ محدودیت شناخته‌شده‌ی معماری (نه باگ): سرویس بات (polling) با مدل `Knative Service` در
  Cloud Run سازگار کامل نیست — به بخش «تصمیم مسیر دیپلوی» در پایین نگاه کن. این مورد
  refactor نشد چون خارج از محدوده‌ی «فقط رفع مشکلات blocking، بدون فیچر جدید» است.

## ۱. فایل تغییریافته در این ممیزی

### `src/bot/main.py`
اضافه شد: فراخوانی `get_ai_provider()` بلافاصله بعد از چک `BOT_TOKEN`، داخل `run_bot()`.
اگر `AI_PROVIDER` یا کلید API متناظرش (`ANTHROPIC_API_KEY`/`GEMINI_API_KEY`/`OPENAI_API_KEY`)
غلط/خالی باشد، بات همان لحظه‌ی استارت با خطای واضح در لاگ متوقف می‌شود — نه اینکه بالا بیاید
و فقط وقتی کاربر اولین عکس را بفرستد خراب شود. هیچ رفتار دیگری تغییر نکرد.

---

## ۲. Secretها و متغیرهای محیطی موردنیاز

قبل از دیپلوی، این مقادیر را (در `.env` برای docker-compose، یا Secret Manager برای Cloud Run) آماده کن:

| متغیر | الزامی؟ | توضیح | نمونه/منبع |
|---|---|---|---|
| `BOT_TOKEN` | **بله** | توکن بات از BotFather | `123456:AA...` |
| `BOT_ADMIN_IDS` | **بله** (برای فیچر ویزیت متخصص) | آیدی عددی تلگرام ادمین‌ها، با کاما جدا | از `@userinfobot` بگیر |
| `AI_PROVIDER` | **بله** | یکی از `claude` / `gemini` / `openai` | پیشنهاد: `claude` |
| کلید AI متناظر | **بله** | فقط کلید پروایدر انتخابی لازم است | `ANTHROPIC_API_KEY` یا `GEMINI_API_KEY` یا `OPENAI_API_KEY` |
| `DATABASE_URL` | **بله** | آدرس Postgres پروداکشن | `postgresql+asyncpg://user:pass@host:5432/db` |
| `POSTGRES_USER/PASSWORD/DB` | فقط برای docker-compose | برای ساخت کانتینر Postgres محلی | |
| `REDIS_URL` | **بله** | برای نگه‌داشتن state مکالمه‌ی بات | `redis://host:6379/0` |
| `SECRET_KEY` | توصیه‌شده | مقدار پیش‌فرض ناامن است، فعلاً در کد استفاده نمی‌شود ولی برای فازهای بعد آماده کن | یک رشته‌ی تصادفی ۶۴ کاراکتری |
| `ADMIN_USERNAME/PASSWORD/SESSION_SECRET` | فعلاً غیرفعال | تعریف شده ولی پنل هنوز لاگین ندارد — **پنل مدیریت را پشت یک IP allowlist یا VPN بگذار تا این فیچر پیاده شود** | |
| `LOG_LEVEL` / `LOG_FORMAT` | خیر | پیش‌فرض `INFO` / `json` مناسب پروداکشن است | |

**قانون طلایی:** فقط کلید AI پروایدری که در `AI_PROVIDER` انتخاب کردی لازم است؛ بقیه را خالی
بگذار.

---

## ۳. تصمیم مسیر دیپلوی (مهم — قبل از شروع تصمیم بگیر)

پروژه دو مسیر دیپلوی آماده دارد. برای MVP v0.1 بین این دو انتخاب کن:

### گزینه‌ی A (پیشنهادی برای v0.1): یک VM ساده یا سرور با `docker-compose`
همه‌چیز (`db`, `redis`, `migrate`, `bot`, `admin`) روی یک ماشین با `docker-compose up -d`
بالا می‌آید. بات polling روی این مدل کاملاً سازگار است، هیچ مشکل زیرساختی ندارد.

### گزینه‌ی B: Google Cloud Run (مانیفست‌های `cloudrun/*.yaml` آماده‌اند)
✅ **پنل مدیریت (`admin-service.yaml`)** روی Cloud Run بدون مشکل کار می‌کند (HTTP سرویس معمولی).

⚠️ **سرویس بات (`bot-service.yaml`)** هیچ HTTP endpoint ندارد (چون polling است) ولی به‌عنوان
Knative `Service` تعریف شده که Cloud Run انتظار دارد روی `$PORT` گوش بدهد. این ناسازگاری
می‌تواند باعث شکست health check/دیپلوی شود. **قبل از دیپلوی بات روی Cloud Run، یکی از این
کارها را انجام بده** (خارج از محدوده‌ی این ممیزی؛ نیاز به تأیید و برنامه‌ریزی جدا دارد):
   - مهاجرت بات به حالت webhook، یا
   - افزودن یک HTTP health endpoint سبک داخل پروسه‌ی بات، یا
   - اجرای بات روی یک GCE VM/Cloud Run Job به‌جای Knative Service

**توصیه‌ی این ممیزی برای v0.1:** بات را با گزینه‌ی A (VM/docker-compose) دیپلوی کن؛ در
صورت تمایل، فقط پنل مدیریت را روی Cloud Run (گزینه‌ی B) ببر.

---

## ۴. مراحل دیپلوی — گزینه‌ی A (docker-compose، پیشنهادی برای v0.1)

- [ ] روی سرور، Docker + Docker Compose نصب است
- [ ] کد را روی سرور بیاور (`git clone` یا آپلود zip)
- [ ] `cp .env.example .env` و همه‌ی مقادیر بخش ۲ را با مقدار واقعی پر کن
- [ ] `AI_PROVIDER` و کلید متناظرش را ست کن
- [ ] `BOT_ADMIN_IDS` را با آیدی تلگرام خودت/تیمت پر کن
- [ ] `docker compose up -d --build` (سرویس `migrate` خودکار مایگریشن‌ها را اجرا می‌کند و
      قبل از بالا آمدن `bot`/`admin` باید موفق تمام شود — به مرحله‌ی بعد نگاه کن)
- [ ] بررسی کن `migrate` موفق بوده: `docker compose logs migrate` — نباید خطا داشته باشد
- [ ] `docker compose run --rm bot python -m scripts.seed` — ادمین‌های `BOT_ADMIN_IDS` را
      در دیتابیس `is_admin=True` می‌کند
- [ ] `docker compose ps` — همه‌ی سرویس‌ها باید `healthy`/`running` باشند
- [ ] `docker compose logs bot --tail=50` — باید خط `bot_starting` و بعد از آن پیام موفقیت
      polling را ببینی، **بدون** خط `ai_provider_misconfigured` (این خط جدید همین ممیزی است)
- [ ] `curl http://localhost:8000/health` → باید `{"status":"ok"}` برگرداند
- [ ] `curl http://localhost:8000/health/ready` → باید `"database": "ok"` نشان بدهد
- [ ] به بات در تلگرام پیام `/start` بده و یک عکس گیاه بفرست — تا انتهای فلوی تشخیص برو

## ۵. مراحل دیپلوی — گزینه‌ی B (Cloud Run، فقط برای پنل مدیریت در v0.1)

- [ ] پروژه‌ی GCP و Artifact Registry آماده است
- [ ] Secretهای موردنیاز در Secret Manager ساخته شده‌اند: `green-vita-database-url`,
      `green-vita-redis-url`, `green-vita-admin-username`, `green-vita-admin-password`,
      `green-vita-admin-session-secret`
- [ ] یک Postgres و Redis قابل‌دسترس از Cloud Run آماده است (Cloud SQL + Memorystore با
      Serverless VPC Access Connector، یا معادل)
- [ ] مایگریشن‌ها را از بیرون (مثلاً از همان محیطی که گزینه‌ی A را اجرا می‌کند، یا یک
      Cloud Run Job جدا) روی همان دیتابیس پروداکشن اجرا کن: `alembic upgrade head`
- [ ] `gcloud run services replace cloudrun/admin-service.yaml --region <REGION>`
- [ ] `curl https://<admin-service-url>/health/ready` را چک کن
- [ ] **بات را روی Cloud Run دیپلوی نکن** تا محدودیت بخش ۳ برطرف شود؛ آن را با گزینه‌ی A اجرا کن

## ۶. تست دود پس از دیپلوی (Smoke Test) — هر دو گزینه

- [ ] `/start` در بات → پیام خوش‌آمد + کیبورد اصلی نمایش داده می‌شود
- [ ] `/help`, `/about` جواب می‌دهند
- [ ] فرستادن یک عکس گیاه → سؤال «اسم گیاه چیه؟» می‌آید
- [ ] پاسخ دادن به سؤالات → نتیجه‌ی تشخیص (۱-تشخیص ← ۲-علت ← ۳-درمان) دریافت می‌شود
- [ ] زدن دکمه‌ی «📞 درخواست ویزیت متخصص گرین‌ویتا» → پیام تأیید به کاربر + پیام اطلاع‌رسانی
      به همه‌ی `BOT_ADMIN_IDS` در تلگرام می‌رسد
- [ ] «🔍 شناسایی گیاه» → عکس → راهنمای کامل نگهداری برمی‌گردد
- [ ] `GET /health` و `GET /health/ready` پنل هر دو ۲۰۰ برمی‌گردانند
- [ ] `GET /` پنل → داشبورد HTML لود می‌شود (به یاد داشته باش: فعلاً **بدون لاگین**، پس تا
      قبل از اضافه‌شدن احراز هویت، URL پنل را عمومی تبلیغ نکن)

## ۷. نکات پایداری برای بعد از انتشار (نه بلاک‌کننده، ولی برای هفته‌ی اول رصد کن)

- هیچ rate limit روی درخواست‌های AI نیست → مصرف API را در پنل Anthropic/OpenAI/Google روزانه چک کن
- هیچ لاگین روی پنل مدیریت نیست → دسترسی شبکه‌ای پنل را محدود نگه‌دار (VPN/IP allowlist/فایروال)
- Redis اگر پایین بیاید، خطا فقط وسط یک مکالمه‌ی کاربر رخ می‌دهد نه در startup → لاگ بات را
  برای خطاهای مربوط به Redis زیر نظر داشته باش
- فهرست کامل این نکات (و موارد غیربلاک‌کننده‌ی دیگر) در `docs/KNOWN_ISSUES.md` هست

---

## ۸. Rollback

- **docker-compose:** `docker compose down` سپس checkout نسخه‌ی قبلی کد و `docker compose up -d --build`
- **مایگریشن دیتابیس:** برای عقب‌گرد یک نسخه: `alembic downgrade -1` (فقط اگر واقعاً لازم
  باشد — مایگریشن‌های این پروژه ستون‌محورند و downgrade هرکدام تعریف شده است)
- **Cloud Run (پنل):** `gcloud run services update-traffic green-vita-admin --to-revisions=<REVISION>=100`
  برای برگشت به revision قبلی بدون rebuild
