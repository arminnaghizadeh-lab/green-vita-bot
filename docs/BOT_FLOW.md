# BOT_FLOW — Green Vita AI Plant Clinic

## نقطه ورود

`src/bot/main.py` → `run_bot()`:
1. `configure_logging()`
2. چک `BOT_TOKEN` (خالی → `ConfigurationError`، بات اصلاً بالا نمی‌آید)
3. ساخت `Bot` با `parse_mode=ParseMode.HTML` پیش‌فرض
4. ساخت `Dispatcher` با `_build_storage()`:
   - تلاش برای `RedisStorage.from_url(settings.redis_url)`
   - اگر ساخت آبجکت خطا بدهد → fallback به `MemoryStorage()` (⚠️ این fallback عملاً همیشه
     موفق می‌شود چون `from_url` اتصال واقعی برقرار نمی‌کند — به `KNOWN_ISSUES.md` نگاه کنید)
5. `bot.delete_webhook(drop_pending_updates=True)` سپس `dp.start_polling(bot)`

## ثبت روترها (`src/bot/handlers/__init__.py`)

ترتیب ثبت **مهم** است چون aiogram هندلرها را به ترتیب ثبت بررسی می‌کند و روی اولین تطابق
متوقف می‌شود:

```
root
 ├── start.router          (/start)
 ├── help.router            (/help)
 ├── about.router            (/about)
 ├── identification.router   ← قبل از diagnosis، چون هندلر عکسِ آن state-scoped است
 └── diagnosis.router         ← هندلر عکسِ آن روی همه‌ی state ها فعال است (fallback عمومی)
```

این ترتیب تضمین می‌کند وقتی کاربر در `IdentificationStates.waiting_photo` است، عکسش برای
شناسایی گونه پردازش شود، نه برای تشخیص بیماری؛ و وقتی کاربر بدون هیچ state خاصی عکس می‌فرستد
(معمول‌ترین حالت)، به‌طور پیش‌فرض وارد فلوی تشخیص بیماری شود.

## Middlewareهای سراسری (`src/bot/middlewares/logging.py`)

هر دو روی `dp.update.outer_middleware` ثبت شده‌اند، یعنی روی **هر نوع Update** (پیام، callback
query، ...) اجرا می‌شوند:

1. **`LoggingMiddleware`** — لاگ ورود هر Update؛ `GreenVitaError` را warning می‌کند و
   دوباره raise می‌کند؛ خطای غیرمنتظره را با `logger.exception` کامل لاگ می‌کند.
2. **`DBSessionMiddleware`** — یک `AsyncSession` تازه می‌سازد، در `data["session"]` می‌گذارد؛
   در پایان پردازش موفق `commit()`، در خطا `rollback()` می‌کند.

## دستورات و دکمه‌های منوی اصلی

| دکمه/دستور | فایل | رفتار |
|---|---|---|
| `/start` | `handlers/start.py` | `get_or_create` کاربر، پیام خوش‌آمد + کیبورد اصلی |
| `/help` | `handlers/help.py` | راهنمای دستورات |
| `/about` | `handlers/about.py` | معرفی کلینیک |
| `📷 تشخیص بیماری` / `/diagnose` | `handlers/diagnosis.py` | پیام راهنما (خودِ فلو با فرستادن عکس شروع می‌شود) |
| `🔍 شناسایی گیاه` / `/identify` | `handlers/identification.py` | `state → IdentificationStates.waiting_photo` |
| `ℹ️ درباره ما` | = `/about` |
| `🆘 راهنما` | = `/help` |

کیبورد اصلی: `src/bot/keyboards/main_menu.py::get_main_menu_keyboard()` — یک `ReplyKeyboardMarkup`
دو ردیفه (تشخیص بیماری + شناسایی گیاه / درباره ما + راهنما).

## فلوی ۱: تشخیص بیماری (`handlers/diagnosis.py`)

State group: `DiagnosisStates` (`src/bot/states.py`)

```
[هر state]  کاربر عکس می‌فرستد
   │  (handle_photo_received — F.photo, بدون قید state)
   ▼
UserRepository.get_or_create()
state.update_data(diagnosis_file_id=...)
state → waiting_plant_name
پیام: "اسم یا نوع این گیاه رو می‌دونی؟"
   │
   ▼  کاربر متن می‌فرستد (handle_plant_name_received)
اگر متن در {"نمی‌دونم","نمیدونم","-"} باشد → plant_name=None
state.update_data(plant_name=...)
state → waiting_plant_details
پیام: "توضیح بیشتری داری؟" + کیبورد inline «رد شدن»
   │
   ├─▶ کاربر متن می‌فرستد (handle_plant_details_received)
   │       user_notes = متن کاربر
   │
   └─▶ کاربر «رد شدن» را می‌زند (handle_skip_details — callback SkipDetailsCallback)
           user_notes = None
   │
   ▼  (هر دو مسیر به _run_diagnosis_and_reply می‌رسند)
bot.download(file_id) → image_bytes
get_ai_provider() → diagnose_plant_image(provider, image_bytes, plant_name, user_notes)
   ├─ AIProviderError → پیام خطای «سرویس هوش مصنوعی در دسترس نیست»، توقف
   └─ Exception دیگر → پیام خطای عمومی، توقف (لاگ کامل با logger.exception)
DiagnosisRepository.create(...)  ← ذخیره‌ی نتیجه (plant_id همیشه None در این فلو)
پیام نهایی: زنجیره‌ی 1️⃣ تشخیص → 2️⃣ علت → 3️⃣ درمان (+ پیشگیری)
   + کیبورد inline: «📞 درخواست ویزیت متخصص گرین‌ویتا» (اگر parse_succeeded)
state.clear()
```

**مسیر ورودی جایگزین:** دکمه‌ی «🩺 تشخیص بیماری» زیر نتیجه‌ی شناسایی گیاه (فلوی ۲) مستقیم
state را به `waiting_plant_details` می‌برد با `plant_name` از قبل پرشده — یعنی سؤال «اسم
گیاه چیه» تکرار نمی‌شود (پیاده‌سازی در `handlers/identification.py::handle_diagnose_from_identification`).

**دکمه‌ی درخواست ویزیت** (`handle_expert_visit_request` — callback `ExpertVisitCallback`):
- اگر `diagnosis.expert_visit_requested` از قبل True بود → فقط alert («قبلاً ثبت شده»).
- وگرنه: `expert_visit_requested=True` می‌شود، به همه‌ی `settings.admin_ids` پیام اطلاع‌رسانی
  فرستاده می‌شود (هر ادمین جدا، خطای هرکدام جدا لاگ و نادیده گرفته می‌شود)، دکمه از پیام کاربر
  حذف می‌شود (`edit_reply_markup(reply_markup=None)`)، پیام تأیید به کاربر.

## فلوی ۲: شناسایی گونه گیاه (`handlers/identification.py`)

State group: `IdentificationStates` (فقط یک state: `waiting_photo`)

```
کاربر «🔍 شناسایی گیاه» یا /identify می‌زند
state → waiting_photo
پیام: "یک عکس واضح بفرست"
   │
   ├─▶ عکس می‌فرستد (handle_identification_photo — state=waiting_photo, F.photo)
   │       state.clear()
   │       bot.download → identify_plant_image() → PlantIdentificationRepository.create()
   │       پیام: نام فارسی/علمی + اطمینان + سختی + راهنمای کامل نگهداری
   │             + کیبورد inline: [🩺 تشخیص بیماری] [📞 درخواست ویزیت متخصص گرین‌ویتا]
   │
   └─▶ چیز دیگری (نه عکس) می‌فرستد (handle_identification_waiting_non_photo — state=waiting_photo)
           پیام: "لطفاً یک عکس بفرست"
```

**دکمه‌ی «🩺 تشخیص بیماری»** (`DiagnoseFromIdentificationCallback`):
`PlantIdentificationRepository.get_by_id` → `state.update_data(diagnosis_file_id, plant_name)`
→ `state → DiagnosisStates.waiting_plant_details` → پیام «توضیح بیشتری داری؟» + کیبورد رد شدن
(از همان کیبورد فلوی ۱ استفاده می‌شود — `get_skip_details_keyboard()`).

**دکمه‌ی «📞 درخواست ویزیت متخصص»** (`IdentificationExpertVisitCallback`): دقیقاً همان منطق
فلوی ۱ ولی روی مدل `PlantIdentification` و با پیام اطلاع‌رسانی مخصوص (شامل نام گیاه شناسایی‌شده
به‌جای نام بیماری).

## کیبوردها (`src/bot/keyboards/`)

| فایل | خروجی |
|---|---|
| `main_menu.py` | `ReplyKeyboardMarkup` منوی اصلی + ثابت‌های متن دکمه‌ها (`BTN_DIAGNOSE`, `BTN_IDENTIFY`, ...) |
| `diagnosis.py` | `SkipDetailsCallback`, `ExpertVisitCallback`, `get_skip_details_keyboard()`, `get_expert_visit_keyboard(diagnosis_id)` |
| `identification.py` | `DiagnoseFromIdentificationCallback`, `IdentificationExpertVisitCallback`, `get_identification_result_keyboard(identification_id)` |

همه‌ی `CallbackData` ها prefix منحصربه‌فرد دارند (`diagskip`, `expvisit`, `iddiag`,
`idexpvisit`) تا تداخلی بین فیلترهای callback پیش نیاید.

## نکات مهم پیاده‌سازی

- **هیچ Rate limiting/throttling روی هندلرها نیست** — کاربر می‌تواند پشت‌سرهم عکس بفرستد و
  هر بار یک فراخوانی پولی به AI Provider بزند.
- **هیچ محدودیت اندازه/نوع فایل روی عکس ورودی نیست** — به `KNOWN_ISSUES.md` نگاه کنید.
- **هیچ global error handler سطح Dispatcher (`dp.error()`) ثبت نشده** — یک استثنای مدیریت‌نشده
  در یک هندلر فقط لاگ می‌شود (توسط `LoggingMiddleware`)؛ کاربر هیچ پیامی دریافت نمی‌کند مگر
  خودِ هندلر صریحاً try/except داشته باشد (که `diagnosis.py` و `identification.py` دارند، ولی
  `start.py`/`help.py`/`about.py` ندارند چون کار خطرناکی انجام نمی‌دهند).
