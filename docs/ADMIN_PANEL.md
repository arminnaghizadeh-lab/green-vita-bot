# ADMIN_PANEL — Green Vita AI Plant Clinic

## وضعیت فعلی: اسکلت اولیه، بدون احراز هویت

پنل مدیریت فقط شامل یک صفحه‌ی داشبورد آماری خیلی ساده و دو health endpoint است. مدیریت
واقعی کاربران/گیاهان/تشخیص‌ها/درخواست‌های ویزیت **هنوز پیاده‌سازی نشده**.

## نقطه ورود

`src/admin/main.py` → `create_app()`:
- `FastAPI(...)` با `docs_url="/docs"` فقط اگر `not settings.is_production` (در production
  مستندات Swagger غیرفعال است)
- `app.mount("/static", StaticFiles(directory="src/admin/static"), name="static")`
- `app.include_router(get_root_router())`
- دو exception handler سراسری:
  - `GreenVitaError` → پاسخ ۴۰۰ با `{"error": code, "message": message}`
  - `Exception` عمومی → پاسخ ۵۰۰ با پیام فارسی عمومی + `logger.exception` کامل

`lifespan` فقط لاگینگ را کانفیگ می‌کند و پیام start/stop لاگ می‌کند — کار خاص دیگری
(مثل warm-up کانکشن دیتابیس) انجام نمی‌دهد.

## روترها (`src/admin/routers/`)

### `health.py`

| مسیر | متد | توضیح |
|---|---|---|
| `/health` | GET | Liveness ساده — همیشه `{"status": "ok"}`، هیچ چک واقعی ندارد |
| `/health/ready` | GET | Readiness — یک `SELECT 1` واقعی روی دیتابیس می‌زند؛ پاسخ شامل `database`, `ai_provider`, `environment` |

### `dashboard.py`

| مسیر | متد | توضیح |
|---|---|---|
| `/` | GET | صفحه‌ی HTML (Jinja2) با تعداد کاربران، تعداد گیاهان، و پروایدر AI فعال |

⚠️ شمارش «تعداد گیاهان» (`Plant`) در این صفحه گمراه‌کننده است چون **هیچ گیاهی در حال حاضر
ثبت نمی‌شود** (به `KNOWN_ISSUES.md` نگاه کنید) — این عدد همیشه ۰ خواهد بود.

## Dependencyها (`src/admin/dependencies.py`)

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]   # از src.db.session.get_db_session
def get_app_settings() -> Settings                                # از src.core.config.get_settings
```

## تمپلیت‌ها (`src/admin/templates/`)

- `base.html` — لایوت پایه، Tailwind از CDN، فونت Tahoma، جهت RTL
- `dashboard.html` — extend از `base.html`، سه کارت آماری + یک بنر هشدار «این نسخه اسکلت اولیه است»

## تنظیمات مرتبط با احراز هویت (تعریف‌شده ولی استفاده‌نشده)

`src/core/config.py` این فیلدها را دارد اما **هیچ‌کدام در `src/admin/` مصرف نمی‌شوند**:

- `admin_username` (پیش‌فرض `"admin"`)
- `admin_password` (پیش‌فرض `"admin"`)
- `admin_session_secret` (پیش‌فرض ناامن)
- `secret_key` (پیش‌فرض ناامن)

یعنی **در وضعیت فعلی، هر کسی که URL پنل مدیریت را داشته باشد بدون هیچ لاگین‌ای به داشبورد
و آمار پایه دسترسی دارد.** جزئیات ریسک در `KNOWN_ISSUES.md` (Critical).

## چه‌چیزی هنوز نیست

- صفحه‌ی لاگین / session management
- مدیریت (لیست/جستجو/ویرایش) کاربران، گیاهان، تشخیص‌ها، شناسایی‌ها
- نمایش درخواست‌های «ویزیت متخصص» (این درخواست‌ها فقط به تلگرام ادمین‌ها فرستاده می‌شوند،
  در پنل هیچ جا دیده نمی‌شوند)
- CORS configuration (فعلاً هیچ `CORSMiddleware`ای ثبت نشده)
- هیچ API نوشتنی (POST/PUT/DELETE) — پنل فعلاً کاملاً read-only (فقط GET)
