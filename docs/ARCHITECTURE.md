# ARCHITECTURE — Green Vita AI Plant Clinic

## نمای کلی لایه‌ها

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   Telegram Bot (aiogram) │     │  Admin Panel (FastAPI)   │
│   src/bot/                │     │  src/admin/               │
└─────────────┬─────────────┘     └─────────────┬─────────────┘
              │                                  │
              │   هر دو سرویس مستقل، هر کدام     │
              │   Process/Container جدا دارند     │
              ▼                                  ▼
┌───────────────────────────────────────────────────────────┐
│                     Repository Layer                        │
│                     src/repositories/                       │
│   تنها نقطه‌ی مجاز برای دسترسی به دیتابیس                    │
└───────────────────────────┬───────────────────────────────┘
                             ▼
┌───────────────────────────────────────────────────────────┐
│                  SQLAlchemy Models + Session                 │
│                     src/db/                                  │
└───────────────────────────┬───────────────────────────────┘
                             ▼
                    PostgreSQL / SQLite

┌───────────────────────────────────────────────────────────┐
│                     AI Provider Layer                        │
│                     src/ai/                                  │
│   base.py (interface) → factory.py (انتخاب با env)          │
│   → providers/{claude,gemini,openai}_provider.py             │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│                     Core (مشترک بین همه)                     │
│                     src/core/                                │
│   config.py (Settings) | logging.py | exceptions.py          │
└───────────────────────────────────────────────────────────┘
```

## پوشه‌بندی و مسئولیت هر بخش

| مسیر | مسئولیت |
|---|---|
| `src/core/` | تنظیمات (`Settings`)، لاگینگ ساختاریافته، استثناهای اختصاصی — مشترک بین بات و پنل |
| `src/db/` | `Base`/`TimestampMixin`، `session.py` (engine + session factory)، `models/` (مدل‌های SQLAlchemy) |
| `src/repositories/` | Repository Pattern — هر مدل یک Repository، همه از `BaseRepository` ارث‌بری می‌کنند |
| `src/ai/` | انتزاع AI Provider + سرویس‌های دامنه (`diagnosis.py`, `plant_identification.py`) + پرامپت‌ها |
| `src/bot/` | هندلرها، کیبوردها، middlewareها، state‌های FSM، نقطه‌ی ورود بات |
| `src/admin/` | اپ FastAPI، روترها، dependencyها، تمپلیت‌های Jinja2 |
| `alembic/` | مایگریشن‌های دیتابیس (async-compatible) |
| `scripts/` | اسکریپت‌های عملیاتی (فعلاً فقط `seed.py`) |
| `docker/`, `cloudrun/`, `.github/workflows/` | زیرساخت Build/Deploy/CI |
| `tests/` | تست‌های واحد (pytest + pytest-asyncio) |

## الگوهای طراحی کلیدی

### ۱. Repository Pattern

هیچ هندلر یا روتی مستقیم SQLAlchemy query نمی‌زند. همه از طریق کلاس‌های `src/repositories/*.py`
(که از `BaseRepository[ModelType]` ارث‌بری می‌کنند) کار می‌کنند. `BaseRepository` عملیات عمومی
(`get_by_id`, `list_all`, `create`, `update`, `delete`) را می‌دهد؛ هر Repository اختصاصی
متدهای دامنه‌ای خودش را اضافه می‌کند (مثل `UserRepository.get_or_create`).

### ۲. AI Provider Abstraction (Strategy Pattern)

`src/ai/base.py` یک اینترفیس انتزاعی (`AIProvider`) با دو متد `chat` و `analyze_image` تعریف
می‌کند. سه پیاده‌سازی مستقل (`ClaudeProvider`, `GeminiProvider`, `OpenAIProvider`) این اینترفیس
را پیاده می‌کنند. `src/ai/factory.py` بر اساس `settings.ai_provider` (مقدار env: `claude` |
`gemini` | `openai`) نمونه‌ی مناسب را می‌سازد. **هیچ کد دیگری در پروژه مستقیماً از SDK یک
شرکت خاص import نمی‌کند** — فقط `providers/*.py` و `factory.py`.

روی این انتزاع، دو سرویس دامنه ساخته شده که پارس خروجی و منطق تخصصی را از هندلر بات جدا می‌کنند:
- `src/ai/diagnosis.py` — `diagnose_plant_image()` + `DiagnosisResult`
- `src/ai/plant_identification.py` — `identify_plant_image()` + `PlantIdentificationResult`

هر دو خروجی مدل را با `json.loads` پارس می‌کنند و در صورت شکست، به‌جای کرش، یک نتیجه‌ی
fallback امن (`parse_succeeded=False`) برمی‌گردانند.

### ۳. Dependency Injection

- **بات:** `DBSessionMiddleware` (در `src/bot/middlewares/logging.py`) یک `AsyncSession` تازه
  به‌ازای هر Update می‌سازد و در `data["session"]` می‌گذارد؛ aiogram این را خودکار به هر
  هندلری که پارامتر `session: AsyncSession` بخواهد تزریق می‌کند. مشابه این برای `bot`, `state`
  هم برقرار است (تزریق داخلی خود aiogram).
- **پنل مدیریت:** از `Depends()` استاندارد FastAPI استفاده می‌شود (`src/admin/dependencies.py`
  → `get_session`, `get_app_settings`).

### ۴. Configuration Management

`src/core/config.py` یک کلاس `Settings(BaseSettings)` واحد (pydantic-settings) دارد که همه‌ی
متغیرهای محیطی را می‌خواند. `get_settings()` با `@lru_cache` کش می‌شود — یعنی در کل عمر
پروسه فقط یک بار serialize/validate می‌شود. **هیچ جای دیگری از کد نباید مستقیم
`os.environ` بخواند.**

### ۵. FSM (Finite State Machine) برای فلوهای چندمرحله‌ای

فلوهایی مثل «تشخیص بیماری» (که چند سوال از کاربر می‌پرسد) با `aiogram.fsm` پیاده شده‌اند.
وضعیت‌ها در `src/bot/states.py` تعریف شده‌اند (`DiagnosisStates`, `IdentificationStates`) و
در Redis نگه داشته می‌شوند (`RedisStorage`، با fallback به `MemoryStorage` اگر Redis در
دسترس نبود — جزئیات در `KNOWN_ISSUES.md`).

## جریان یک درخواست معمول (مثال: تشخیص بیماری)

```
کاربر عکس می‌فرستد
   → Update وارد Dispatcher می‌شود
   → LoggingMiddleware (لاگ ورودی)
   → DBSessionMiddleware (باز کردن AsyncSession)
   → روتر diagnosis → handle_photo_received()
        → UserRepository.get_or_create()
        → state.set_state(DiagnosisStates.waiting_plant_name)
   ...چند پیام رفت‌وبرگشت با کاربر...
   → handle_plant_details_received() یا handle_skip_details()
        → bot.download() → دانلود عکس از تلگرام
        → get_ai_provider() → diagnose_plant_image()
             → AIProvider.analyze_image() → پارس JSON → DiagnosisResult
        → DiagnosisRepository.create() → ذخیره در دیتابیس
        → ارسال پیام فرمت‌شده + کیبورد «درخواست ویزیت متخصص»
   → DBSessionMiddleware: session.commit() (خودکار در پایان Update)
```

## چرا دو سرویس جدا (bot / admin)؟

- مقیاس‌پذیری مستقل: پنل ادمین می‌تواند scale-to-zero باشد، بات نمی‌تواند (polling).
- Deploy مستقل: تغییر در پنل نیازی به ری‌استارت بات ندارد و برعکس.
- محدودسازی دسترسی: در آینده می‌توان پنل را پشت IAM/VPC قرار داد بدون تأثیر روی بات.

جزئیات بیشتر درباره‌ی محدودیت این معماری روی Cloud Run (بات polling در برابر مدل
request-driven) در `KNOWN_ISSUES.md` و `DEPLOYMENT.md` آمده است.
