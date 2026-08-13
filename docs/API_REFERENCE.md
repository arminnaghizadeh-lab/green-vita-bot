# API_REFERENCE — Green Vita AI Plant Clinic

پروژه فعلاً **فقط یک API عمومی HTTP** دارد: سرویس پنل مدیریت (FastAPI،
`src/admin/main.py`). بات تلگرام از طریق long-polling کار می‌کند و هیچ HTTP endpoint ای
expose نمی‌کند.

> در `APP_ENV=production`، مستندات خودکار Swagger (`/docs`) غیرفعال است
> (`docs_url=None`). در توسعه/staging روی `/docs` در دسترس است.

## `GET /health`

Liveness probe ساده.

**پاسخ ۲۰۰:**
```json
{ "status": "ok" }
```

هیچ چک واقعی‌ای (دیتابیس، Redis، ...) انجام نمی‌دهد — فقط تأیید می‌کند پروسه بالا است.

## `GET /health/ready`

Readiness probe — یک `SELECT 1` واقعی روی دیتابیس اجرا می‌کند.

**پاسخ ۲۰۰ (سالم):**
```json
{
  "status": "ok",
  "database": "ok",
  "ai_provider": "claude",
  "environment": "production"
}
```

**پاسخ ۲۰۰ با `status: "degraded"` (دیتابیس در دسترس نیست):**
```json
{
  "status": "degraded",
  "database": "error: <پیام خطای SQLAlchemy>",
  "ai_provider": "claude",
  "environment": "production"
}
```
⚠️ توجه: حتی در حالت خطای دیتابیس، status code همچنان ۲۰۰ است، نه ۵۰۳ — این می‌تواند
load balancer/Cloud Run را گمراه کند که سرویس سالم است (به `KNOWN_ISSUES.md` نگاه کنید).

## `GET /`

صفحه‌ی HTML داشبورد (نه JSON) — رندر شده با Jinja2 از `src/admin/templates/dashboard.html`.
شامل: تعداد کاربران، تعداد گیاهان (فعلاً همیشه ۰)، پروایدر AI فعال، محیط اجرا (`environment`).

**بدون هیچ احراز هویتی در دسترس عموم است.**

## `GET /static/*`

فایل‌های استاتیک از `src/admin/static/` (فعلاً فقط یک `.gitkeep`، هیچ CSS/JS اختصاصی
سرو نمی‌شود؛ استایل از Tailwind CDN در `base.html` می‌آید).

## Error Handling سراسری

هر دو exception handler در `src/admin/main.py` ثبت شده‌اند:

| نوع استثنا | Status Code | بدنه‌ی پاسخ |
|---|---|---|
| `GreenVitaError` (و زیرکلاس‌هایش، مثل `ValidationError`, `NotFoundError`) | ۴۰۰ | `{"error": "<code>", "message": "<پیام فارسی>"}` |
| هر `Exception` دیگر | ۵۰۰ | `{"error": "internal_error", "message": "خطای داخلی سرور رخ داد."}` |

توجه: همه‌ی `GreenVitaError`ها فعلاً با کد ۴۰۰ برگردانده می‌شوند، حتی مثلاً
`AuthenticationError` (که منطقاً باید ۴۰۱ باشد) یا `NotFoundError` (که منطقاً باید ۴۰۴
باشد) — چون این exception handler هنوز کد وضعیت را بر اساس نوع دقیق استثنا تفکیک نمی‌کند.

## چیزی که در API نیست (هنوز)

- هیچ endpoint نوشتنی (POST/PUT/PATCH/DELETE)
- هیچ endpoint برای لیست/جستجوی کاربران، گیاهان، تشخیص‌ها، شناسایی‌ها، درخواست‌های ویزیت
- هیچ authentication/authorization (API key، session، JWT، ...)
- هیچ versioning (`/v1/...`)
- هیچ rate limiting
- هیچ CORS middleware (اگر در آینده یک فرانت‌اند جدا این API را صدا بزند، نیاز است)
