# 🌿 Green Vita AI Plant Clinic

دستیار هوشمند تلگرامی کلینیک گیاه‌پزشکی **گرین‌ویتا** — فاز ۱: پایه و معماری پروژه.

> ⚠️ در این فاز فقط **اسکلت پروژه** آماده شده: دستورات `/start` `/help` `/about` با پاسخ
> placeholder کار می‌کنند. تشخیص بیماری، پرونده گیاه، یادآوری و فروشگاه در فازهای بعدی
> اضافه می‌شوند.

---

## 🏗 معماری

```
green-vita-bot/
├── src/
│   ├── bot/              # ربات تلگرام (aiogram 3)
│   │   ├── handlers/      # هندلرهای دستورات
│   │   ├── middlewares/   # لاگ‌گیری + تزریق DB session
│   │   └── keyboards/     # کیبوردهای بات
│   ├── admin/             # پنل مدیریت (FastAPI)
│   │   ├── routers/       # health, dashboard
│   │   └── templates/     # Jinja2 + Tailwind
│   ├── core/               # config, logging, exceptions
│   ├── db/                 # مدل‌های SQLAlchemy + session
│   ├── repositories/       # Repository Pattern (لایه دسترسی به داده)
│   └── ai/                 # لایه انتزاع هوش مصنوعی
│       └── providers/      # Claude / Gemini / OpenAI
├── alembic/                # مایگریشن‌های دیتابیس
├── tests/                  # تست‌های واحد (pytest + pytest-asyncio)
├── docker/                 # Dockerfile های بات و ادمین
├── cloudrun/                # مانیفست‌های Cloud Run
├── .github/workflows/      # CI/CD
├── scripts/seed.py         # داده اولیه (ادمین‌ها)
└── docker-compose.yml
```

### تصمیم‌های معماری کلیدی

| تصمیم | دلیل |
|---|---|
| **Repository Pattern** | جدا کردن منطق دیتابیس از هندلرها/روت‌ها — تست‌پذیری بالاتر |
| **AI Provider Abstraction** | تعویض Claude/Gemini/OpenAI فقط با یک متغیر env، بدون تغییر کد |
| **Async همه‌جا** | aiogram 3 و FastAPI هر دو async هستند؛ SQLAlchemy async engine هماهنگ با هر دو |
| **دو سرویس جدا (bot/admin)** | مقیاس‌پذیری و دیپلوی مستقل روی Cloud Run |
| **SQLite fallback** | توسعه لوکال بدون نیاز به Postgres؛ فقط `DATABASE_URL` عوض می‌شود |

---

## ⚙️ پیش‌نیازها

- Python 3.12+
- Docker + Docker Compose (برای اجرای کامل استک)
- یک بات تلگرام ساخته‌شده با [@BotFather](https://t.me/BotFather) (توکن آن را داری)
- کلید API حداقل یکی از: Claude (Anthropic) / Gemini (Google) / OpenAI

---

## 🚀 راه‌اندازی سریع (Docker — پیشنهادی)

```bash
# ۱. کلون/کپی پروژه و ورود به پوشه
cd green-vita-bot

# ۲. ساخت فایل .env از روی نمونه
cp .env.example .env

# ۳. مقادیر زیر را در .env پر کن (حداقل‌ها):
#    BOT_TOKEN=...           (از BotFather)
#    AI_PROVIDER=claude      (یا gemini / openai)
#    ANTHROPIC_API_KEY=...   (متناسب با AI_PROVIDER)
#    BOT_ADMIN_IDS=...       (آیدی عددی تلگرام خودت، از @userinfobot بگیر)

# ۴. بالا آوردن کل استک (Postgres + Redis + Bot + Admin)
make docker-up
# یا: docker compose up -d --build

# ۵. اجرای مایگریشن‌ها (اتوماتیک هم اجرا می‌شود، ولی برای اطمینان دستی هم می‌شود):
docker compose run --rm migrate

# ۶. ساخت کاربر ادمین اولیه (بر اساس BOT_ADMIN_IDS در .env)
docker compose run --rm bot python -m scripts.seed
```

پنل مدیریت روی `http://localhost:8000` بالا می‌آید و `/health` باید `{"status": "ok"}` برگرداند.
به بات در تلگرام پیام `/start` بده.

---

## 🖥 راه‌اندازی لوکال (بدون Docker)

```bash
python3.12 -m venv .venv
source .venv/bin/activate

make install          # وابستگی‌های اصلی
make dev-install      # + وابستگی‌های تست/لینت

cp .env.example .env
# DATABASE_URL را به sqlite تغییر بده برای سادگی:
# DATABASE_URL=sqlite+aiosqlite:///./greenvita.db

make migrate           # اجرای مایگریشن‌ها
make seed              # ساخت ادمین اولیه

# در دو ترمینال جدا:
make run-bot            # اجرای بات
make run-admin           # اجرای پنل مدیریت
```

---

## 🤖 تعویض پروایدر هوش مصنوعی

فقط کافیست در `.env` مقدار `AI_PROVIDER` را عوض کنی — **هیچ کد دیگری نیاز به تغییر ندارد**:

```env
AI_PROVIDER=claude     # یا: gemini | openai
```

و کلید API متناظرش را پر کن (`ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY`).
منطق سوییچ در `src/ai/factory.py` است.

---

## 🧪 تست

```bash
make test          # pytest + گزارش پوشش کد
make lint          # ruff + mypy
make format        # فرمت خودکار
```

تست‌ها روی SQLite in-memory اجرا می‌شوند، نیازی به Postgres واقعی نیست.

---

## ☁️ دیپلوی روی Cloud Run

پایپ‌لاین `.github/workflows/ci-cd.yml` به‌صورت خودکار روی push به `main`:
1. لینت و تست را اجرا می‌کند
2. ایمیج‌های `bot` و `admin` را می‌سازد و به Artifact Registry push می‌کند
3. هر دو سرویس را روی Cloud Run دیپلوی می‌کند

**Secrets موردنیاز در GitHub repo:**
`GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`, `GCP_REGION`

**نکته مهم درباره بات روی Cloud Run:** بات در این فاز با polling کار می‌کند که نیاز به
یک نمونه‌ی همیشه-روشن دارد (`minScale=1` در `cloudrun/bot-service.yaml` همین را تضمین می‌کند).
برای کاهش هزینه در فازهای بعدی می‌توان به حالت **webhook** مهاجرت کرد که با مدل
scale-to-zero کلود ران سازگارتر است.

دیپلوی دستی (بدون CI):
```bash
gcloud run services replace cloudrun/bot-service.yaml --region <REGION>
gcloud run services replace cloudrun/admin-service.yaml --region <REGION>
```

---

## 🗺 نقشه راه فازهای بعدی

- [x] تشخیص بیماری گیاه از روی عکس (عکس + سوال از کاربر → Claude/Gemini/OpenAI → تشخیص + توصیه درمانی)
- [x] دکمه‌ی «درخواست ویزیت متخصص گرین‌ویتا» + اطلاع‌رسانی به ادمین‌ها
- [x] شناسایی گونه گیاه از روی عکس (نام فارسی/علمی + راهنمای کامل نگهداری)
- [ ] گفتگوی تخصصی گیاه‌پزشکی با کانتکست پرونده گیاه
- [ ] یادآوری آبیاری/کوددهی (APScheduler + Cloud Scheduler)
- [ ] پرونده درمانی کامل هر گیاه (تاریخچه، عکس‌ها، وضعیت) — ثبت رسمی گیاه، نه فقط ورودی متنی تشخیص
- [ ] فروشگاه و پیشنهاد محصول
- [ ] هدایت به ویزیت آنلاین (تکمیل جریان «درخواست ویزیت» با رزرو واقعی)
- [ ] احراز هویت کامل پنل مدیریت (session/JWT)
- [ ] مدیریت کامل کاربران/گیاهان/محصولات در پنل
- [ ] نمایش لیست دیاگنوزها و درخواست‌های ویزیت در پنل مدیریت

### 🌿 فلوی تشخیص بیماری (فاز ۲)

1. کاربر عکس گیاه را می‌فرستد.
2. بات اسم/نوع گیاه را می‌پرسد (قابل رد شدن با «نمی‌دونم»).
3. بات توضیح تکمیلی اختیاری می‌پرسد (قابل رد شدن با دکمه).
4. عکس + پاسخ‌های کاربر به پروایدر AI فعال (`AI_PROVIDER` در `.env`، پیش‌فرض Claude) فرستاده می‌شود.
5. نتیجه (تشخیص، شدت، اطمینان، علائم، **علت**، درمان، پیشگیری) پارس، در جدول `diagnoses` ذخیره و برای کاربر طبق زنجیره‌ی **۱) تشخیص ← ۲) علت ← ۳) درمان** با فرمت خوانا ارسال می‌شود.
6. کاربر می‌تواند دکمه‌ی «📞 درخواست ویزیت متخصص گرین‌ویتا» را بزند — همه‌ی آیدی‌های `BOT_ADMIN_IDS` پیام اطلاع‌رسانی با خلاصه‌ی تشخیص و اطلاعات تماس کاربر دریافت می‌کنند.

### 🔍 فلوی شناسایی گیاه (فاز ۲.۱)

1. کاربر دکمه‌ی «🔍 شناسایی گیاه» یا دستور `/identify` را می‌زند.
2. عکس گیاه را می‌فرستد.
3. عکس به پروایدر AI فعال فرستاده می‌شود و نتیجه شامل نام فارسی، نام علمی، درصد اطمینان،
   سطح سختی نگهداری، نور/آبیاری/رطوبت/دما/خاک/کود/گلدان/تعویض گلدان، روش‌های تکثیر،
   آفت‌ها و بیماری‌های رایج، سمیت برای حیوانات خانگی و انسان، و نکات پیشگیرانه است.
4. نتیجه در جدول `plant_identifications` ذخیره و برای کاربر با فرمت خوانا ارسال می‌شود،
   همراه با دو دکمه:
   - **🩺 تشخیص بیماری** — مستقیم وارد فلوی diagnosis می‌شود (بدون سوال دوباره‌ی اسم گیاه،
     چون از نتیجه‌ی شناسایی گرفته می‌شود)
   - **📞 درخواست ویزیت متخصص گرین‌ویتا** — مشابه فلوی تشخیص بیماری، به ادمین‌ها اطلاع می‌دهد

---

## 📄 لایسنس

مالکیت خصوصی — کلینیک گیاه‌پزشکی گرین‌ویتا.
