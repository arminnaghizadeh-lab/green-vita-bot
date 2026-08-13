# MVP_DEPLOYMENT_PLAN — Green Vita v0.1-baseline (Polling)

> این مستند فقط پلن است. هیچ فایل پروژه تغییر نکرده، هیچ commit ای انجام نشده، هیچ دیپلوی
> واقعی انجام نشده. مبتنی بر بررسی مستقیم `docker-compose.yml`, `docker/Dockerfile.bot`,
> `docker/Dockerfile.admin`, `.env.example`, و `Makefile` موجود در ریپو — بدون هیچ تغییر در
> این فایل‌ها.

---

## ۱. پلتفرم پیشنهادی و چرایی

**پیشنهاد: یک VPS ساده (Hetzner Cloud یا DigitalOcean) که فقط `docker compose up -d`
روی آن اجرا می‌شود — بدون Kubernetes، بدون Cloud Run، بدون هیچ لایه‌ی orchestration اضافه.**

چرا:
- معماری فعلی بات **polling** است — یعنی یک پروسه‌ی همیشه-روشن با یک اتصال طولانی به
  تلگرام لازم دارد، نه یک پلتفرم request-driven/scale-to-zero (طبق تحلیل
  `DEPLOYMENT_STRATEGY.md`، این محدودیت از خودِ Telegram Bot API می‌آید).
- `docker-compose.yml` پروژه از قبل کامل و برای دقیقاً همین سناریو (یک ماشین، همه‌چیز کنار
  هم: `db` + `redis` + `migrate` + `bot` + `admin`) نوشته شده — هیچ تطبیق یا تغییری لازم
  ندارد.
- ساده‌ترین مسیر با کمترین بخش متحرک = کمترین ریسک برای اولین انتشار پروداکشن.
- هزینه‌ی ثابت و قابل‌پیش‌بینی (یک سرور کوچک ۲ هسته/۴ گیگ رم کافی است؛ نیازی به سرویس‌های
  مدیریت‌شده‌ی جدا برای Postgres/Redis نیست چون هر دو همین الان به‌عنوان کانتینر در همان
  `docker-compose.yml` تعریف شده‌اند).

**جایگزین معتبر:** هر VPS دیگری که Docker + Docker Compose را پشتیبانی کند (Linode،
Vultr، یک سرور اختصاصی داخلی، …) — انتخاب Hetzner/DigitalOcean فقط به‌خاطر قیمت و
سادگی است، نه یک وابستگی فنی به آن‌ها.

⚠️ **نکته‌ی عملیاتی:** برخی ارائه‌دهنده‌های بزرگ ابری (از جمله DigitalOcean/AWS/GCP) به‌خاطر
تحریم‌ها ممکن است ثبت‌نام/پرداخت از ایران را نپذیرند. قبل از انتخاب نهایی پلتفرم، دسترسی و
روش پرداخت را با همون ارائه‌دهنده تأیید کن؛ اگر محدودیتی بود، یک VPS منطقه‌ای/داخلی جایگزین
(هر ارائه‌دهنده‌ای که Docker را پشتیبانی کند) با همین پلن دقیقاً کار می‌کند — هیچ تغییری در
مراحل زیر لازم نیست.

---

## ۲. نیازمندی‌های دقیق سرور/سرویس

| مورد | حداقل | توصیه‌شده |
|---|---|---|
| CPU | ۱ vCPU | ۲ vCPU |
| RAM | ۲ گیگابایت | ۴ گیگابایت |
| دیسک | ۲۰ گیگابایت SSD | ۴۰ گیگابایت SSD |
| سیستم‌عامل | Ubuntu 22.04 LTS یا 24.04 LTS | همان |
| نرم‌افزار لازم | Docker Engine ۲۴+ و Docker Compose v2 (plugin) | همان |
| پورت‌های باز (فایروال) | `22` (SSH)، `8000` (پنل مدیریت) | + `443`/`80` اگر بعداً دامنه/TLS برای پنل اضافه شود |
| دسترسی خروجی اینترنت | به `api.telegram.org` و endpoint پروایدر AI انتخابی (`api.anthropic.com` / `generativelanguage.googleapis.com` / `api.openai.com`) | الزامی — بدون این، نه بات نه AI کار می‌کند |

توضیح رم: سه کانتینر پایتون (bot, admin, migrate یک‌بار) + Postgres + Redis روی یک VPS
۲ گیگابایتی جا می‌شود ولی تنگ است؛ ۴ گیگابایت حاشیه‌ی امن‌تری می‌دهد، خصوصاً چون هر دو
Dockerfile حین build از `build-essential` استفاده می‌کنند (پیک مصرف حافظه در زمان build،
نه در زمان اجرا).

---

## ۳. متغیرهای محیطی لازم (`.env`)

همه از `.env.example` موجود در ریپو کپی می‌شوند (`cp .env.example .env`). مقادیری که
**باید** با مقدار واقعی جایگزین شوند (نه پیش‌فرض نمونه):

| متغیر | چرا الزامی است |
|---|---|
| `BOT_TOKEN` | بدون آن بات اصلاً استارت نمی‌شود (چک `ConfigurationError` در `src/bot/main.py`) |
| `BOT_ADMIN_IDS` | برای دریافت اطلاع‌رسانی «درخواست ویزیت متخصص» و برای `scripts/seed.py` |
| `AI_PROVIDER` | یکی از `claude` / `gemini` / `openai` — از v0.1-baseline به بعد، بدون کلید معتبر متناظر، **بات از استارت هم امتناع می‌کند** (اصلاح جدید در `src/bot/main.py`) |
| کلید AI متناظر | فقط همان یکی که در `AI_PROVIDER` انتخاب شده: `ANTHROPIC_API_KEY` یا `GEMINI_API_KEY` یا `OPENAI_API_KEY` |
| `DATABASE_URL` | برای این پلن دست‌نخورده می‌ماند: `postgresql+asyncpg://greenvita:greenvita@db:5432/greenvita` (هاست `db` = نام سرویس Postgres در `docker-compose.yml`، نیاز به تغییر ندارد مگر رمز عبور را عوض کنی) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | باید با هم و با `DATABASE_URL` هماهنگ باشند — پیشنهاد: رمز پیش‌فرض `greenvita` را در پروداکشن عوض کن و در هر دو جا (این سه متغیر + `DATABASE_URL`) یکسان به‌روزرسانی کن |
| `REDIS_URL` | دست‌نخورده می‌ماند: `redis://redis:6379/0` |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_SESSION_SECRET` | فعلاً در کد استفاده نمی‌شوند (پنل هنوز لاگین ندارد — `docs/KNOWN_ISSUES.md`، مورد C1)؛ همچنان مقدارشان را از پیش‌فرض ناامن عوض کن تا برای فاز بعدی (افزودن auth) آماده باشد |
| `SECRET_KEY` | فعلاً در کد استفاده نمی‌شود؛ همچنان یک مقدار تصادفی بگذار |
| `LOG_LEVEL=INFO`, `LOG_FORMAT=json` | مقدار پیش‌فرض برای پروداکشن مناسب است، تغییر لازم نیست |
| `APP_ENV=production` | باعث می‌شود `/docs` (Swagger) پنل غیرفعال شود — برای پروداکشن لازم است |

---

## ۴. Secretهای لازم (خارج از پروژه، باید از قبل تهیه شوند)

| Secret | منبع | استفاده |
|---|---|---|
| توکن بات تلگرام | [@BotFather](https://t.me/BotFather) | `BOT_TOKEN` |
| آیدی عددی تلگرام ادمین(ها) | [@userinfobot](https://t.me/userinfobot) | `BOT_ADMIN_IDS` |
| کلید API پروایدر AI انتخابی | کنسول Anthropic / Google AI Studio / OpenAI | `ANTHROPIC_API_KEY` یا `GEMINI_API_KEY` یا `OPENAI_API_KEY` |
| رمز عبور Postgres پروداکشن | خودت تولید کن (مثلاً `openssl rand -hex 16`) | `POSTGRES_PASSWORD` + بخش رمز در `DATABASE_URL` |
| SSH key برای دسترسی به VPS | خودت/تیمت | دسترسی سرور |

هیچ Secret دیگری برای این مسیر دیپلوی (docker-compose روی VPS) لازم نیست — چیزهایی مثل
`GCP_*` Secretهای موجود در `.github/workflows/ci-cd.yml` فقط برای مسیر Cloud Run هستند و
در این پلن استفاده نمی‌شوند.

---

## ۵. دستورات دقیق دیپلوی

```bash
# ۱) روی VPS (یک‌بار، هنگام راه‌اندازی سرور)
apt-get update && apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# ۲) انتقال کد به سرور
git clone <آدرس ریپازیتوری> green-vita-bot
cd green-vita-bot
git checkout v0.1-baseline    # قفل‌کردن دقیقاً روی نسخه‌ی تأییدشده

# ۳) تنظیم env
cp .env.example .env
nano .env    # پر کردن همه‌ی مقادیر بخش ۳

# ۴) بیلد و بالا آوردن کل استک
docker compose up -d --build

# ۵) بررسی این‌که migrate موفق تمام شده (مرحله‌ی بعد را ببین)
docker compose logs migrate

# ۶) ساخت ادمین اولیه در دیتابیس (بر اساس BOT_ADMIN_IDS در .env)
docker compose run --rm bot python -m scripts.seed
```

---

## ۶. روال مایگریشن دیتابیس

مایگریشن به‌صورت **خودکار** توسط سرویس `migrate` در `docker-compose.yml` انجام می‌شود:

- سرویس `migrate` منتظر سالم‌شدن `db` می‌ماند (`depends_on: db: condition: service_healthy`)
- سپس دقیقاً `alembic upgrade head` را اجرا و خارج می‌شود
- سرویس‌های `bot` و `admin` هر دو منتظر می‌مانند تا `migrate` با موفقیت **کامل** تمام شود
  (`condition: service_completed_successfully`) — یعنی اگر مایگریشن شکست بخورد، نه بات نه
  پنل بالا نمی‌آیند (رفتار امن پیش‌فرض، بدون نیاز به تغییر).

بررسی دستی موفقیت:
```bash
docker compose logs migrate
# باید خط "Running upgrade ... -> 0005" (یا مشابه) را ببینی، بدون Traceback
```

اجرای دستی مجدد (مثلاً بعد از یک مایگریشن جدید در آینده):
```bash
docker compose run --rm migrate
# یا معادل: docker compose run --rm bot alembic upgrade head
```

وضعیت فعلی: ۵ مایگریشن (`0001` تا `0005`)، زنجیره‌ی خطی، در `v0.1-baseline` تأیید شده.

---

## ۷. نحوه‌ی استارت بات تلگرام

بات به‌صورت یک سرویس همیشه-روشن در `docker-compose.yml` تعریف شده (`restart: unless-stopped`):

1. کانتینر `bot` بالا می‌آید → `src/bot/main.py::main()` اجرا می‌شود
2. چک `BOT_TOKEN` (خالی → توقف فوری با خطای واضح)
3. **(اصلاح جدید در v0.1-baseline)** چک پیکربندی AI Provider — کلید API غلط/خالی → توقف
   فوری با خطای واضح در لاگ، قبل از اینکه هیچ کاربری متوجه مشکل شود
4. `bot.delete_webhook(drop_pending_updates=True)` — برای اطمینان از اینکه هیچ webhook
   قدیمی فعال نیست و بات در حالت polling خالص کار می‌کند
5. `dp.start_polling(bot)` — از این لحظه بات آماده‌ی دریافت پیام است

هیچ اقدام دستی برای «استارت» بات لازم نیست جز بالا نگه‌داشتن کانتینر (`restart: unless-stopped`
این کار را بعد از ریبوت سرور یا کرش هم خودکار انجام می‌دهد).

---

## ۸. نحوه‌ی دسترسی به پنل مدیریت

- آدرس: `http://<IP-سرور>:8000/`
- ⚠️ **بدون احراز هویت است** (`docs/KNOWN_ISSUES.md`، مورد C1) — این پلن دیپلوی، طبق
  محدودیت صریح این وظیفه («بدون فیچر جدید، بدون تغییر معماری»)، auth اضافه نمی‌کند.
  **اقدام لازم (عملیاتی، نه کد):** پورت `8000` را در فایروال VPS فقط برای IPهای مشخص
  (تیم خودت) باز بگذار، یا از طریق SSH tunnel به آن دسترسی پیدا کن:
  ```bash
  ssh -L 8000:localhost:8000 user@<IP-سرور>
  # سپس http://localhost:8000 را در مرورگر لوکال خودت باز کن
  ```
  تا زمانی که فیچر لاگین اضافه نشده، **پورت ۸۰۰۰ را عمومی در اینترنت باز نگه ندار.**

---

## ۹. نحوه‌ی تأیید اینکه بات واقعاً کار می‌کند

```bash
# ۱) همه‌ی سرویس‌ها بالا و healthy هستند؟
docker compose ps

# ۲) لاگ استارت بات را ببین — نباید خطای ai_provider_misconfigured یا ConfigurationError باشد
docker compose logs bot --tail=50

# ۳) پنل مدیریت زنده است؟
curl http://localhost:8000/health
# انتظار: {"status":"ok"}

curl http://localhost:8000/health/ready
# انتظار: "database": "ok"
```

**تست دود واقعی (از طریق خود تلگرام):**
1. در تلگرام به بات پیام `/start` بده → باید پیام خوش‌آمد + کیبورد اصلی برگردد
2. یک عکس گیاه بفرست → باید سؤال «اسم گیاه چیه؟» بیاید
3. جواب بده → باید نتیجه‌ی تشخیص (۱-تشخیص ← ۲-علت ← ۳-درمان) برگردد
4. دکمه‌ی «📞 درخواست ویزیت متخصص گرین‌ویتا» را بزن → باید پیام اطلاع‌رسانی به تلگرام
   `BOT_ADMIN_IDS` برسد

اگر همه‌ی این ۴ مرحله جواب دادند، بات در پروداکشن سالم است.

---

## ۱۰. نحوه‌ی ری‌استارت سرویس‌ها

```bash
# ری‌استارت فقط بات (مثلاً بعد از تغییر .env)
docker compose restart bot

# ری‌استارت فقط پنل مدیریت
docker compose restart admin

# ری‌استارت کل استک
docker compose restart

# ری‌استارت کامل با rebuild (بعد از pull کد جدید)
docker compose down
docker compose up -d --build
```

توجه: `restart` مقادیر `.env` را دوباره نمی‌خواند اگر کانتینر عوض نشود در برخی حالت‌ها؛
برای اطمینان کامل بعد از تغییر `.env`، از `docker compose up -d` (نه فقط `restart`)
استفاده کن — Compose خودش تشخیص می‌دهد کانتینر باید recreate شود.

---

## ۱۱. نحوه‌ی مشاهده‌ی لاگ‌ها

```bash
# لاگ زنده‌ی همه‌ی سرویس‌ها
docker compose logs -f
# یا: make docker-logs

# فقط بات
docker compose logs -f bot

# فقط پنل مدیریت
docker compose logs -f admin

# ۱۰۰ خط آخر بات (بدون follow)
docker compose logs bot --tail=100
```

لاگ‌ها با `structlog` در فرمت JSON هستند (`LOG_FORMAT=json`) — هر خط یک JSON مستقل با
فیلدهای `event`, `level`, `timestamp` و کانتکست اضافی (مثل `telegram_user_id`) است؛ برای
خوانایی بهتر حین دیباگ دستی می‌توان با `jq` فیلتر کرد:
```bash
docker compose logs bot --tail=200 | grep -o '{.*}' | jq .
```

---

## ۱۲. روال Rollback

### اگر دیپلوی جدید مشکل داشت (برگشت به `v0.1-baseline`)

```bash
cd green-vita-bot
docker compose down
git fetch --tags
git checkout v0.1-baseline
docker compose up -d --build
```

### اگر یک مایگریشن جدید (در آینده) مشکل ایجاد کرد

```bash
docker compose run --rm bot alembic downgrade -1
# سپس کد را هم به نسخه‌ی قبل از آن مایگریشن برگردان (git checkout)
```

### اگر فقط یک سرویس (نه کل دیپلوی) مشکل داشت

```bash
# برگرداندن فقط ایمیج بات به بیلد قبلی (اگر ایمیج قدیمی هنوز لوکال موجود است)
docker compose up -d --no-build bot   # با تگ/ایمیج قبلی که Docker کش کرده
```

### نکته‌ی مهم Rollback

از همین حالا (`v0.1-baseline`) به بعد، هر دیپلوی پروداکشن باید روی یک **git tag مشخص**
انجام شود (نه مستقیم روی `main`) — دقیقاً همین الگویی که `v0.1-baseline` شروع کرده. این
تضمین می‌کند rollback همیشه یعنی «checkout تگ قبلی»، نه حدس‌زدن آخرین commit سالم.

---

## نتیجه‌گیری نهایی

همه‌ی فایل‌های لازم برای این مسیر دیپلوی (`docker-compose.yml`, هر دو `Dockerfile`,
`.env.example`, ۵ مایگریشن Alembic, `scripts/seed.py`) از قبل در `v0.1-baseline` کامل و
سالم هستند — طبق ممیزی‌های قبلی (`RELEASE_NOTES.md`, `DEPLOY_CHECKLIST.md`) هیچ مشکل
blocking در خودِ کد پیدا نشده. تنها پیش‌نیازهای باقی‌مانده، کارهای بیرون از کد هستند
(تهیه‌ی VPS، secretها، اجرای دستورات بالا) که مسئولیت خودِ تیم دیپلوی است، نه محدودیت کد.

# READY TO DEPLOY
