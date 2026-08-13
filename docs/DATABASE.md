# DATABASE — Green Vita AI Plant Clinic

## موتور و اتصال

- ORM: SQLAlchemy 2.0 (async، `Mapped`/`mapped_column`)
- پروداکشن: PostgreSQL 16 (درایور `asyncpg`)
- توسعه لوکال: SQLite (درایور `aiosqlite`) — فقط با تغییر `DATABASE_URL`، بدون تغییر کد
- Session factory: `src/db/session.py` → `AsyncSessionLocal` (یک Engine سراسری، یک Session
  تازه به ازای هر واحد کار)
- تمام مدل‌ها از `Base` + `TimestampMixin` (`src/db/base.py`) ارث‌بری می‌کنند که خودکار
  `created_at` / `updated_at` (هر دو `DateTime(timezone=True)`) اضافه می‌کند.

## نمودار روابط (ER خلاصه)

```
User (1) ──── (N) Plant
User (1) ──── (N) Conversation
User (1) ──── (N) Reminder
User (1) ──── (N) Diagnosis
User (1) ──── (N) PlantIdentification

Plant (1) ──── (N) Conversation   (nullable FK)
Plant (1) ──── (N) Reminder
Plant (1) ──── (N) Diagnosis      (nullable FK — در عمل فعلاً همیشه NULL، به KNOWN_ISSUES.md نگاه کنید)
```

## مدل‌ها

### User — `src/db/models/user.py`

| فیلد | نوع | توضیح |
|---|---|---|
| `id` | int, PK | |
| `telegram_id` | BigInteger, unique, indexed | آیدی عددی تلگرام کاربر |
| `username`, `first_name`, `last_name` | str، nullable | از پروفایل تلگرام |
| `phone_number` | str، nullable | فعلاً هیچ هندلری آن را پر نمی‌کند |
| `language_code` | str، nullable | |
| `is_admin` | bool، پیش‌فرض False | فقط `scripts/seed.py` آن را برای `BOT_ADMIN_IDS` تنظیم می‌کند |
| `is_blocked` | bool، پیش‌فرض False | تعریف‌شده ولی جایی در کد چک نمی‌شود |

روابط: `plants`, `conversations`, `reminders`, `diagnoses`, `plant_identifications` (همه
`cascade="all, delete-orphan"`).

### Plant — `src/db/models/plant.py`

| فیلد | نوع | توضیح |
|---|---|---|
| `id` | int, PK | |
| `owner_id` | FK → users.id (CASCADE) | |
| `name` | str، نال‌نشدنی | |
| `species` | str، nullable | |
| `notes` | Text، nullable | |
| `health_status` | Enum `PlantHealthStatus` | `healthy` \| `sick` \| `under_treatment` \| `recovered` \| `unknown` |

⚠️ **این مدل تعریف شده اما هیچ هندلر بات فعلاً رکورد `Plant` نمی‌سازد یا نمی‌خواند** (فاز
«پرونده گیاه» هنوز پیاده نشده). فیلد `Plant.health_status` قبلاً (در پیاده‌سازی اولیه‌ی
diagnosis) بعد از هر تشخیص آپدیت می‌شد، اما در بازنویسی فاز ۲ (که سؤال «اسم گیاه» را جایگزین
انتخاب از لیست گیاهان کرد) این اتصال حذف شد — به `KNOWN_ISSUES.md` نگاه کنید.

### Conversation — `src/db/models/conversation.py`

| فیلد | نوع | توضیح |
|---|---|---|
| `id` | int, PK | |
| `user_id` | FK → users.id (CASCADE) | |
| `plant_id` | FK → plants.id (SET NULL)، nullable | |
| `role` | Enum `MessageRole` | `user` \| `assistant` \| `system` |
| `content` | Text | |
| `ai_provider` | str، nullable | |

⚠️ **این مدل تعریف شده اما هیچ کدی فعلاً از آن استفاده نمی‌کند** — برای فاز «گفتگوی تخصصی
گیاه‌پزشکی» رزرو شده.

### Reminder — `src/db/models/reminder.py`

| فیلد | نوع | توضیح |
|---|---|---|
| `id` | int, PK | |
| `user_id` | FK → users.id (CASCADE) | |
| `plant_id` | FK → plants.id (CASCADE) | |
| `reminder_type` | Enum `ReminderType` | `watering` \| `fertilizing` \| `other` |
| `interval_days` | int، پیش‌فرض 7 | |
| `next_run_at` | DateTime(timezone=True) | |
| `is_active` | bool، پیش‌فرض True | |

⚠️ **این مدل تعریف شده اما هیچ Scheduler/Job ای فعلاً آن را اجرا نمی‌کند** — برای فاز
«یادآوری آبیاری/کوددهی» رزرو شده.

### Diagnosis — `src/db/models/diagnosis.py`

نتیجه‌ی هر تشخیص بیماری از روی عکس.

| فیلد | نوع | توضیح |
|---|---|---|
| `id` | int, PK | |
| `user_id` | FK → users.id (CASCADE) | |
| `plant_id` | FK → plants.id (SET NULL)، nullable | در عمل فعلاً همیشه `NULL` (نگاه کنید به بالا) |
| `telegram_file_id` | str | برای دانلود دوباره‌ی عکس بدون ذخیره‌ی باینری |
| `plant_name_input` | str، nullable | اسم/نوع گیاهی که خود کاربر تایپ کرده |
| `user_notes` | Text، nullable | توضیح تکمیلی اختیاری کاربر |
| `is_healthy` | bool | |
| `disease_name` | str، پیش‌فرض «نامشخص» | |
| `severity` | Enum `DiagnosisSeverity` | `none` \| `mild` \| `moderate` \| `severe` \| `unknown` |
| `confidence` | int (۰ تا ۱۰۰) | |
| `symptoms` | Text، nullable | هر علامت در یک خط (`\n`-joined) |
| `cause` | Text، nullable | علت ریشه‌ای (فاز ۳) |
| `treatment` | Text، nullable | |
| `prevention` | Text، nullable | |
| `ai_provider` | str | کدام پروایدر پاسخ داده (`claude`/`gemini`/`openai`) |
| `raw_response` | Text، nullable | متن خام خروجی مدل، برای دیباگ |
| `expert_visit_requested` | bool، پیش‌فرض False | |

### PlantIdentification — `src/db/models/plant_identification.py`

نتیجه‌ی هر شناسایی گونه‌ی گیاه از روی عکس.

| فیلد | نوع | توضیح |
|---|---|---|
| `id` | int, PK | |
| `user_id` | FK → users.id (CASCADE) | |
| `telegram_file_id` | str | |
| `persian_name` | str، پیش‌فرض «نامشخص» | |
| `scientific_name` | str، nullable | |
| `confidence` | int (۰ تا ۱۰۰) | |
| `difficulty_level` | Enum `DifficultyLevel` | `easy` \| `medium` \| `hard` \| `unknown` |
| `light_requirement`, `watering_schedule`, `humidity`, `temperature`, `soil_mix`, `fertilizer_recommendation`, `potting_advice`, `repotting_interval` | Text، nullable | راهنمای نگهداری |
| `propagation_methods`, `common_pests`, `common_diseases` | Text، nullable | هر مورد در یک خط |
| `toxicity_pets`, `toxicity_humans` | Text، nullable | |
| `preventive_care_tips` | Text، nullable | |
| `ai_provider` | str | |
| `raw_response` | Text، nullable | |
| `expert_visit_requested` | bool، پیش‌فرض False | |

## Enumها (خلاصه)

| Enum | مقادیر | تعریف‌شده در |
|---|---|---|
| `PlantHealthStatus` | healthy, sick, under_treatment, recovered, unknown | `plant.py` |
| `MessageRole` | user, assistant, system | `conversation.py` |
| `ReminderType` | watering, fertilizing, other | `reminder.py` |
| `DiagnosisSeverity` | none, mild, moderate, severe, unknown | `diagnosis.py` |
| `DifficultyLevel` | easy, medium, hard, unknown | `plant_identification.py` |

همه‌ی Enumها هم Python `str, enum.Enum` هستند (برای سریال‌سازی راحت در Repository/AI layer)
و هم SQLAlchemy `Enum` در ستون دیتابیس (Postgres این‌ها را به‌صورت native enum type می‌سازد).

## مایگریشن‌ها (`alembic/versions/`)

| Revision | فایل | تغییر |
|---|---|---|
| `0001` | `0001_initial_schema.py` | ساخت جدول‌های `users`, `plants`, `conversations`, `reminders` |
| `0002` | `0002_add_diagnoses_table.py` | ساخت جدول `diagnoses` |
| `0003` | `0003_diagnosis_intake_fields.py` | افزودن `plant_name_input`, `user_notes`, `expert_visit_requested` به `diagnoses` |
| `0004` | `0004_add_plant_identifications_table.py` | ساخت جدول `plant_identifications` |
| `0005` | `0005_add_cause_to_diagnoses.py` | افزودن `cause` به `diagnoses` |

اجرا: `alembic upgrade head` یا `make migrate`. مایگریشن‌ها async-compatible هستند
(`alembic/env.py` از `async_engine_from_config` استفاده می‌کند) و آدرس دیتابیس را مستقیم از
`src.core.config.get_settings()` می‌خوانند — یعنی همیشه با همان `DATABASE_URL` که بات/پنل
استفاده می‌کنند هماهنگ است.

## Repository Layer (`src/repositories/`)

| Repository | متدهای اختصاصی (علاوه بر CRUD پایه) |
|---|---|
| `UserRepository` | `get_by_telegram_id`, `get_or_create`, `list_admins` |
| `PlantRepository` | `list_by_owner`, `count_all` |
| `ConversationRepository` | `list_by_user` (ترتیب قدیم→جدید) |
| `ReminderRepository` | `list_by_plant`, `list_due` |
| `DiagnosisRepository` | `list_by_plant`, `list_by_user` |
| `PlantIdentificationRepository` | `list_by_user` |

`BaseRepository[ModelType]` (در `src/repositories/base.py`) عملیات مشترک را می‌دهد:
`get_by_id`, `list_all`, `create`, `update`, `delete`.
