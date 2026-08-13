# PROJECT_OVERVIEW — Green Vita AI Plant Clinic

## هدف پروژه

دستیار هوشمند تلگرامی برای کلینیک گیاه‌پزشکی «گرین‌ویتا» که به کاربران کمک می‌کند:

- گونه‌ی گیاهشان را از روی عکس بشناسند
- بیماری/آفت گیاه را از روی عکس تشخیص دهند (به همراه علت و درمان)
- در صورت نیاز، درخواست ویزیت متخصص ثبت کنند

پنل مدیریت (FastAPI) هم برای مشاهده‌ی آمار پایه در نظر گرفته شده که هنوز در مراحل اولیه است.

## وضعیت فعلی (تا این مستند)

| فاز | عنوان | وضعیت |
|---|---|---|
| ۱ | اسکلت پروژه (معماری، Docker، CI/CD، مدل‌های پایه) | ✅ کامل |
| ۲ | تشخیص بیماری از عکس | ✅ کامل |
| ۲.۱ | شناسایی گونه گیاه از عکس | ✅ کامل |
| ۳ | زنجیره‌ی تشخیص ← علت ← درمان | ✅ کامل |
| — | یادآوری آبیاری/کوددهی | ❌ پیاده‌سازی نشده (فقط مدل `Reminder` در دیتابیس هست) |
| — | پرونده رسمی گیاه (ثبت/مدیریت) | ❌ پیاده‌سازی نشده (فقط مدل `Plant` هست، بدون هندلر بات) |
| — | گفتگوی آزاد گیاه‌پزشکی | ❌ پیاده‌سازی نشده (فقط مدل `Conversation` هست) |
| — | فروشگاه و پیشنهاد محصول | ❌ پیاده‌سازی نشده |
| — | احراز هویت پنل مدیریت | ❌ پیاده‌سازی نشده (پنل کاملاً باز است — نگاه کنید به `KNOWN_ISSUES.md`) |

## اجزای اصلی سیستم

1. **بات تلگرام** (`src/bot`) — با aiogram 3، روی polling اجرا می‌شود.
2. **پنل مدیریت** (`src/admin`) — FastAPI، فقط داشبورد آماری ساده + health check.
3. **لایه‌ی هوش مصنوعی** (`src/ai`) — انتزاع روی Claude / Gemini / OpenAI.
4. **دیتابیس** (`src/db`, `alembic`) — PostgreSQL (پروداکشن) یا SQLite (توسعه لوکال)، از طریق SQLAlchemy async.
5. **لایه‌ی Repository** (`src/repositories`) — تنها نقطه‌ی دسترسی به دیتابیس.
6. **زیرساخت Deploy** — Docker، docker-compose، Cloud Run manifests، GitHub Actions.

## پشته‌ی فناوری (Tech Stack)

| لایه | فناوری |
|---|---|
| زبان | Python 3.12 |
| بات تلگرام | aiogram 3.15 (async, polling) |
| API/پنل | FastAPI 0.115 + Jinja2 + Tailwind (CDN) |
| ORM | SQLAlchemy 2.0 (async) |
| مایگریشن | Alembic (async-compatible) |
| دیتابیس | PostgreSQL 16 (پروداکشن) / SQLite (dev) |
| کش/FSM Storage | Redis 7 |
| هوش مصنوعی | Anthropic Claude / Google Gemini / OpenAI (قابل سوییچ با env) |
| کانتینر | Docker + docker-compose |
| Deploy | Google Cloud Run (دو سرویس جدا: bot و admin) |
| CI/CD | GitHub Actions |
| تست | pytest + pytest-asyncio |
| لاگ | structlog (JSON در پروداکشن) |

## نقشه‌ی سریع فایل‌های مستندات

- `ARCHITECTURE.md` — لایه‌ها، الگوهای طراحی، جریان یک درخواست
- `DATABASE.md` — مدل‌ها، روابط، مایگریشن‌ها
- `AI_MODULE.md` — انتزاع پروایدر AI، پرامپت‌ها، پارس خروجی
- `BOT_FLOW.md` — تمام فلوهای مکالمه‌ی بات، state به state
- `ADMIN_PANEL.md` — روت‌ها و وضعیت فعلی پنل
- `DEPLOYMENT.md` — Docker، docker-compose، Cloud Run، CI/CD
- `API_REFERENCE.md` — endpointهای HTTP پنل مدیریت
- `KNOWN_ISSUES.md` — محدودیت‌ها و بدهی‌های فنی شناخته‌شده
