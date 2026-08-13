# AI_MODULE — Green Vita AI Plant Clinic

## هدف

جدا کردن کامل منطق دامنه (تشخیص بیماری، شناسایی گیاه) از SDK هر شرکت خاص، طوری که
**تعویض پروایدر فقط با یک متغیر محیطی (`AI_PROVIDER`) ممکن باشد** و هیچ کد دیگری تغییر نکند.

## ساختار فایل‌ها

```
src/ai/
├── base.py                    # اینترفیس انتزاعی AIProvider + انواع داده مشترک
├── factory.py                 # ساخت نمونه‌ی پروایدر بر اساس Settings.ai_provider
├── prompts.py                 # پرامپت‌های تشخیص بیماری (سیستم + کاربر)
├── diagnosis.py               # سرویس دامنه: diagnose_plant_image + DiagnosisResult
├── plant_identification.py    # سرویس دامنه: identify_plant_image + PlantIdentificationResult
└── providers/
    ├── claude_provider.py     # پیاده‌سازی با Anthropic SDK
    ├── gemini_provider.py     # پیاده‌سازی با google-generativeai SDK
    └── openai_provider.py     # پیاده‌سازی با OpenAI SDK
```

## اینترفیس `AIProvider` (`base.py`)

```python
class AIProvider(ABC):
    name: str

    async def chat(self, messages: list[ChatMessage], *, system_prompt=None) -> AIResponse: ...
    async def analyze_image(self, image_bytes: bytes, *, prompt: str, system_prompt=None) -> AIResponse: ...
```

- `ChatMessage(role: ChatRole, content: str)` — `ChatRole` یکی از `user` / `assistant`.
- `AIResponse(text, provider, model, raw={})` — خروجی استاندارد‌شده‌ی هر سه پروایدر.
- `chat()` فعلاً در هیچ‌جای بات استفاده نمی‌شود (برای فاز «گفتگوی آزاد» رزرو شده)؛ فقط
  `analyze_image()` در حال حاضر مصرف‌کننده دارد.

## پیاده‌سازی‌های پروایدر

| پروایدر | فایل | SDK | مدل پیش‌فرض (env) |
|---|---|---|---|
| Claude | `claude_provider.py` | `anthropic.AsyncAnthropic` | `ANTHROPIC_MODEL` (پیش‌فرض `claude-sonnet-4-6`) |
| Gemini | `gemini_provider.py` | `google.generativeai` | `GEMINI_MODEL` (پیش‌فرض `gemini-2.0-flash`) |
| OpenAI | `openai_provider.py` | `openai.AsyncOpenAI` | `OPENAI_MODEL` (پیش‌فرض `gpt-4o`) |

`OpenAIProvider` یک پارامتر اختیاری `base_url` هم می‌پذیرد (از `OPENAI_BASE_URL` در env).
این برای استفاده از gatewayهای سازگار با فرمت OpenAI است — مثلاً پلتفرم‌های ایرانی مثل
AvalAI/GapGPT که دسترسی به مدل‌های Claude/Gemini را هم از پشت یک API سازگار با OpenAI
ارائه می‌دهند (مفید برای زمانی که دسترسی مستقیم/پرداخت بین‌المللی به API رسمی Anthropic
ممکن نیست). در این حالت معمولاً `AI_PROVIDER=openai` و `OPENAI_MODEL` روی نام مدل واقعی
(مثلاً `claude-sonnet-4-6`) تنظیم می‌شود. اگر `OPENAI_BASE_URL` خالی بماند، رفتار قبلی
(آدرس رسمی OpenAI) بدون تغییر باقی می‌ماند.

نکات مشترک هر سه پیاده‌سازی:
- سازنده (`__init__`) اگر `api_key` خالی باشد بلافاصله `AIProviderError` می‌اندازد (fail-fast).
- هر دو متد `chat`/`analyze_image` با دکوریتور `tenacity.retry` پوشانده شده‌اند:
  حداکثر ۳ تلاش، backoff نمایی بین ۱ تا ۸ ثانیه.
- خطای هر SDK (Exception عمومی) گرفته و به `AIProviderError` تبدیل می‌شود — کد بالادستی
  فقط با استثناهای خودمان (`src/core/exceptions.py`) سروکار دارد، نه با خطاهای خاص هر SDK.
- تصویر همیشه به‌صورت base64 (`image/jpeg`) فرستاده می‌شود.
- **هیچ‌کدام timeout صریح روی کلاینت HTTP تنظیم نکرده‌اند** — به `KNOWN_ISSUES.md` نگاه کنید.

## `factory.py` — انتخاب پروایدر

```python
def build_ai_provider(settings: Settings) -> AIProvider: ...
def get_ai_provider() -> AIProvider   # @lru_cache — نمونه‌ی سراسری کش‌شده
```

`build_ai_provider` بر اساس `settings.ai_provider` (`"claude"` | `"gemini"` | `"openai"`)
یکی از سه کلاس بالا را می‌سازد. مقدار نامعتبر → `ConfigurationError`. کلید API خالی برای
پروایدر انتخاب‌شده → `AIProviderError` (از داخل سازنده‌ی همان پروایدر).

هندلرهای بات همیشه از `get_ai_provider()` استفاده می‌کنند، نه ساخت مستقیم کلاس.

## سرویس‌های دامنه

### `diagnosis.py`

```python
async def diagnose_plant_image(ai_provider, image_bytes, *, plant_name=None, user_notes=None) -> DiagnosisResult
```

جریان: `build_diagnosis_user_prompt()` (از `prompts.py`) + `DIAGNOSIS_SYSTEM_PROMPT` →
`ai_provider.analyze_image()` → `parse_diagnosis_response()`.

`DiagnosisResult` (dataclass): `is_healthy`, `disease_name`, `severity`, `confidence`,
`symptoms: list[str]`, `cause`, `treatment`, `prevention`, `ai_provider`, `raw_response`,
`parse_succeeded`.

`parse_diagnosis_response()`:
- code fenceهای ```` ```json ... ``` ```` را strip می‌کند.
- `json.loads` می‌کند؛ `severity` نامعتبر → `UNKNOWN`؛ `confidence` به بازه‌ی ۰-۱۰۰ کلمپ می‌شود.
- در صورت شکست پارس (`JSONDecodeError`/`ValueError`/`TypeError`): یک `DiagnosisResult` با
  `parse_succeeded=False` برمی‌گرداند که متن خام مدل را در `treatment` می‌گذارد — طوری که
  کاربر همیشه یک پاسخ (هرچند غیرساختاریافته) می‌بیند، نه خطای خام.

### `plant_identification.py`

الگوی کاملاً مشابه `diagnosis.py`، برای شناسایی گونه:

```python
async def identify_plant_image(ai_provider, image_bytes) -> PlantIdentificationResult
```

`PlantIdentificationResult` شامل ۱۷ فیلد ساختاریافته است (نام فارسی/علمی، اطمینان، سطح
سختی، نور/آبیاری/رطوبت/دما/خاک/کود/گلدان/تعویض گلدان، تکثیر، آفت/بیماری رایج، سمیت
حیوان/انسان، نکات پیشگیرانه) — دقیقاً منطبق بر ستون‌های مدل `PlantIdentification`.

## پرامپت‌ها (`prompts.py`)

`DIAGNOSIS_SYSTEM_PROMPT` پرسونای «گیاه‌پزشک متخصص کلینیک گرین‌ویتا» را تعریف می‌کند و
مدل را مجبور می‌کند **فقط JSON خالص** برگرداند (بدون ` ```json `، بدون توضیح اضافه). قوانین
کلیدی پرامپت:
1. خروجی فقط یک شیء JSON معتبر.
2. اگر عکس گیاه نبود → `is_healthy=false`, `disease_name="تصویر نامشخص یا نامرتبط"`.
3. گیاه سالم → `disease_name="سالم"`.
4. زنجیره‌ی استدلال اجباری: **تشخیص ← علت (`cause`) ← درمان (`treatment`)** — این قانون در
   فاز ۳ اضافه شد.

پرامپت مشابه برای شناسایی گیاه در `plant_identification.py` تعریف شده
(`PLANT_ID_SYSTEM_PROMPT`)، نه در `prompts.py` — این دو فایل هم‌ساختارند اما فایل جدا دارند.

`build_diagnosis_user_prompt(plant_name, user_notes)` پیام کاربر (همراه عکس) را می‌سازد؛
شامل اسمی که کاربر تایپ کرده و توضیح تکمیلی‌اش (اگر داده باشد).

## نمودار فراخوانی کامل (تشخیص بیماری)

```
handlers/diagnosis.py
   → get_ai_provider()                         [factory.py]
   → diagnose_plant_image(provider, image, ...)  [ai/diagnosis.py]
        → build_diagnosis_user_prompt(...)       [ai/prompts.py]
        → provider.analyze_image(...)            [ai/providers/*.py]
             → SDK فراخوانی + retry + خطا→AIProviderError
        → parse_diagnosis_response(...)          [ai/diagnosis.py]
   ← DiagnosisResult
```

## تست‌های موجود

`tests/test_ai_factory.py` — ساخت درست هر سه پروایدر با `AI_PROVIDER` مربوطه، خطای
`AIProviderError` روی کلید خالی، خطای `ConfigurationError` روی مقدار نامعتبر.

`tests/test_diagnosis_ai.py` — پارس JSON معتبر، حذف code fence، کلمپ `confidence`،
`severity` نامعتبر → `UNKNOWN`، fallback روی JSON نامعتبر، ساخت پرامپت کاربر با/بدون
`plant_name`/`user_notes`، پارس فیلد `cause`.

⚠️ **هیچ تستی برای `plant_identification.py` یا برای providers (`claude_provider.py` و...)
نوشته نشده** — به `KNOWN_ISSUES.md` نگاه کنید.
