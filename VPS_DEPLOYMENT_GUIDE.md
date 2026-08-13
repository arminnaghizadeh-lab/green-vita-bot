# VPS_DEPLOYMENT_GUIDE — Green Vita v0.1 (Polling)

> این مستند فقط راهنماست. هیچ کد/فایل پروژه‌ای تغییر نکرده، هیچ commit ای انجام نشده،
> هیچ دیپلوی واقعی انجام نشده. مبتنی بر commit `09236f09ca2289cbf1c8dfa626b2f492ef72daed`
> (شاخه‌ی `main`) که تأیید شده هم پشتیبانی `OPENAI_BASE_URL` (AvalAI) و هم volume پایدار
> Redis (`redisdata`) را همزمان دارد — نه تگ قدیمی‌تر `v0.1-baseline` که فاقد هر دوی
> این‌هاست. همچنین شامل اصلاحات یافته‌شده در آخرین ممیزی است.

## ✅ الزام volume پایدار Redis برطرف شد

در نسخه‌ی قبلی این راهنما، Redis هیچ volume پایداری نداشت. این مورد در commit
`09236f0` (`docker-compose.yml`) با افزودن volume نام‌گذاری‌شده‌ی `redisdata` روی مسیر
`/data` برطرف شده. الان هم Postgres (`pgdata`) و هم Redis (`redisdata`) هر دو volume
پایدار دارند — بخش ۶ (بررسی وضعیت) این را تأیید می‌کند.

---

## ۱. مشخصات پیشنهادی VPS

| مورد | حداقل | توصیه‌شده |
|---|---|---|
| CPU | ۲ vCPU | ۲ vCPU (کافیه) |
| RAM | ۲ گیگابایت (+ ۲ گیگ swap اجباری) | ۴ گیگابایت |
| دیسک | ۲۰ گیگابایت SSD/NVMe | ۴۰ گیگابایت |
| **لوکیشن** | **خارج از ایران** (آلمان/فنلاند/فرانسه) | همان — چون Telegram API از داخل ایران معمولاً فیلتره |
| پهنای باند | نامحدود یا حداقل چند صد گیگ/ماه | نامحدود |

> همون سروری که قبلاً بررسی کردیم (Hetzner آلمان، ۲ core / ۲GB RAM / ۲۰GB NVMe) با اضافه‌کردن
> ۲ گیگ swap کاملاً کافیه — نیازی به ارتقا نیست.

## ۲. توزیع لینوکس پیشنهادی

**Ubuntu 22.04 LTS** یا **Ubuntu 24.04 LTS** — پرکاربردترین و بادوام‌ترین گزینه برای Docker،
مستندات و پشتیبانی جامعه‌ی گسترده، بدون نیاز به تنظیم خاص اضافه.

## ۳. نرم‌افزارهای لازم

| نرم‌افزار | برای چی |
|---|---|
| Docker Engine (`docker-ce`) | اجرای کانتینرها |
| Docker Compose plugin (`docker-compose-plugin`) | اجرای `docker compose` |
| `git` | آوردن کد روی سرور |
| `ufw` | فایروال سطح سرور |
| `fail2ban` (پیشنهادی) | جلوگیری از brute-force روی SSH |
| `curl`, `unzip` | ابزار کمکی نصب/انتقال فایل |

---

## ۴. نصب Docker + Docker Compose

```bash
apt-get update
apt-get install -y ca-certificates curl gnupg git ufw fail2ban

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker    # ← لازم برای الزام ۹/۱۰: بعد از ریبوت سرور، Docker خودش بالا بیاد
systemctl start docker

docker --version
docker compose version
```

### ساخت swap (چون RAM سرور ۲ گیگه)

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
free -h   # باید ردیف Swap: 2.0Gi رو ببینی
```

---

## ۵. فایروال (الزامات امنیتی ۱، ۲، ۳، ۴)

### ⚠️ نکته‌ی فنی مهم درباره‌ی Docker + ufw

Docker مستقیم قوانین `iptables` خودش رو تزریق می‌کنه که می‌تونه از قوانین معمولی `ufw`
عبور کنه — یعنی صرفاً `ufw deny 5432` ممکنه **کافی نباشه** برای بستن پورتی که Docker
منتشرش کرده. راه درست، اضافه‌کردن قانون مستقیم به زنجیره‌ی `DOCKER-USER` هست (این یک
تنظیم سطح سرور/فایروالِه، نه تغییر کد پروژه):

```bash
# ۱) فعال‌سازی ufw با پیش‌فرض «همه چیز بسته»
ufw default deny incoming
ufw default allow outgoing

# ۲) فقط SSH و پنل مدیریت (الزام ۳ و ۴)
ufw allow 22/tcp
ufw allow from <IP-ثابت-خودت> to any port 8000 proto tcp   # ← IP خودت رو جایگزین کن
# اگه IP ثابت نداری، به‌جای این خط از SSH tunnel استفاده کن (بخش ۱۲) و اصلاً پورت ۸۰۰۰ رو باز نذار

ufw enable
ufw status verbose
```

```bash
# ۳) بستن واقعی ۵۴۳۲ و ۶۳۷۹ در برابر دسترسی بیرونی (الزام ۱ و ۲)
# این قانون مستقیم به iptables اضافه می‌شود چون ufw به‌تنهایی کافی نیست.
#
# فیلتر بر اساس اینترفیس ورودی، نه IP مبدأ — چون فیلتر بر اساس IP مبدأ (مثل ! -s 127.0.0.1)
# غیرقابل‌اعتماده: بسته به تنظیم کرنل bridge-nf-call-iptables، ممکنه ترافیک داخلی
# کانتینر-به-کانتینر (bot→db, migrate→redis, ...) رو هم اشتباهی DROP کنه و کل سرویس رو
# بخوابونه. فیلتر بر اساس اینترفیس، مستقل از اون تنظیمه و تضمینی کار می‌کنه.

PUB_IF=$(ip -o -4 route show to default | awk '{print $5}')
echo "اینترفیس عمومی: $PUB_IF"   # ← مطمئن شو خالی نیست، مثلاً eth0 یا ens3

iptables -I DOCKER-USER -i "$PUB_IF" -p tcp --dport 5432 -j DROP
iptables -I DOCKER-USER -i "$PUB_IF" -p tcp --dport 6379 -j DROP

# ماندگار کردن این قوانین بعد از ریبوت:
apt-get install -y iptables-persistent
netfilter-persistent save
```

### تأیید اعمال‌شدن قوانین (اجباری — قبل از رفتن به مرحله‌ی بعد)

```bash
iptables -L DOCKER-USER -n --line-numbers
```

**چیزی که باید تو خروجی ببینی:** دو خط `DROP` برای پورت‌های `5432` و `6379`، مرتبط با
اینترفیس عمومی (`$PUB_IF`) — چیزی شبیه زیر (ترتیب شماره‌ی خط می‌تونه فرق کنه، مهم وجود
همین دو خط با `DROP` و نام اینترفیس درسته):
```
num  target     prot opt in     source               destination
1    DROP       tcp  --  eth0   0.0.0.0/0            0.0.0.0/0            tcp dpt:5432
2    DROP       tcp  --  eth0   0.0.0.0/0            0.0.0.0/0            tcp dpt:6379
```
اگه این دو خط رو ندیدی، یا ستون `in` به‌جای اینترفیس عمومی چیز دیگه‌ای نشون داد، یعنی
قانون درست اعمال نشده — **قبل از باز کردن سرور به اینترنت متوقف شو** و دوباره دستورات
بالا رو اجرا کن.

### تنظیمات SSH (الزام ۴)

```bash
# قبل از این مرحله مطمئن شو SSH key-based login برات جواب می‌ده (تست از یه ترمینال جدا)
nano /etc/ssh/sshd_config
```
این مقادیر رو تنظیم کن:
```
PasswordAuthentication no
PermitRootLogin prohibit-password
```
سپس:
```bash
systemctl restart sshd
```

---

## ۶. آوردن کد روی سرور (Git Deployment)

```bash
cd /root
git clone <آدرس-ریپازیتوری-تو> green-vita-bot
cd green-vita-bot
git checkout 09236f09ca2289cbf1c8dfa626b2f492ef72daed
git log -1 --oneline          # باید دقیقاً 09236f0 نشون بده

# تأیید دوتایی که این commit واقعاً هر دو تغییر لازم رو داره:
grep -q "openai_base_url" src/core/config.py && echo "OK: openai_base_url present" || echo "MISSING: openai_base_url — متوقف شو"
grep -q "redisdata" docker-compose.yml && echo "OK: redisdata volume present" || echo "MISSING: redisdata — متوقف شو"
```

⚠️ **از `git checkout v0.1-baseline` استفاده نکن.** آن تگ به یک commit قدیمی‌تر
(`2c43bf7`) اشاره می‌کند که فاقد پشتیبانی `OPENAI_BASE_URL` (لازم برای AvalAI) و فاقد
volume پایدار Redis (`redisdata`) است — استفاده از آن یعنی دیپلوی یک نسخه‌ی ناقص.

> اگه هنوز ریپازیتوری روی GitHub/GitLab نداری، جایگزین: zip پروژه رو با `scp` از کامپیوتر
> خودت به سرور منتقل کن و `unzip` کن — کارکرد بعدی فرقی نمی‌کنه، فقط مطمئن شو zipی که
> منتقل می‌کنی از commit `09236f0` یا جدیدتر گرفته شده باشه.

---

## ۷. تنظیم `.env` (الزامات امنیتی ۵ و ۶)

```bash
cp .env.example .env
chmod 600 .env      # فقط خودِ root بتونه بخونه/بنویسه
nano .env
```

مقادیر لازم رو پر کن (`BOT_TOKEN`, `BOT_ADMIN_IDS`, `AI_PROVIDER` + کلید متناظر،
`POSTGRES_PASSWORD` + بخش رمز در `DATABASE_URL`، `SECRET_KEY`, `ADMIN_PASSWORD`,
`ADMIN_SESSION_SECRET`).

**تضمین اینکه `.env` هیچ‌وقت وارد Git نمی‌شه:**
```bash
git check-ignore -v .env
# باید خروجی بده: .gitignore:11:.env    .env
# اگه هیچی چاپ نشد یعنی مشکل داره — فوراً متوقف شو و بگو
```

---

## ۸. مایگریشن دیتابیس

### ۸.۰ اعتبارسنجی اجباری Compose (قبل از هر `up`/`run`)

```bash
docker compose config
```
این دستور فقط فایل رو پارس و validate می‌کنه، هیچ کانتینری بالا نمی‌آره. اگه با خطا خارج
شد (exit code غیرصفر، یا پیام خطای YAML/schema)، **متوقف شو و ادامه نده** — یعنی جایی تو
`.env` یا خودِ فایل مشکل داره. فقط اگه بدون خطا کل کانفیگ resolve‌شده رو چاپ کرد، برو مرحله‌ی بعد.

```bash
docker compose up -d db redis     # اول فقط دیتابیس و ردیس رو بالا بیار
docker compose logs -f db          # صبر کن تا healthy بشه (Ctrl+C برای خروج از لاگ)

docker compose run --rm migrate    # اجرای دستی مایگریشن (یا با up کامل خودکار هم اجرا می‌شه)
docker compose logs migrate        # باید بدون Traceback باشه، آخرین خط چیزی شبیه "...-> 0005" 
```

---

## ۹. بالا آوردن کامل سرویس‌ها (الزامات ۷، ۹، ۱۰)

```bash
docker compose up -d --build
```

این دستور:
- همه‌ی سرویس‌ها (`db`, `redis`, `migrate`, `bot`, `admin`) رو بالا میاره
- `bot`/`admin` با هم فقط از طریق شبکه‌ی داخلی Docker Compose (نام سرویس‌ها: `db`, `redis`)
  حرف می‌زنن — نه از طریق اینترنت عمومی (الزام ۷، از قبل در معماری برقراره)
- چون `restart: unless-stopped` روی `bot`/`admin`/`db`/`redis` تنظیمه، بعد از کرش یا ریبوت
  سرور (تا وقتی `systemctl enable docker` زده باشی)، خودکار دوباره بالا میان (الزام ۹، ۱۰)

## ۱۰. بررسی وضعیت سرویس‌ها

```bash
docker compose ps
```
انتظار: همه‌ی سرویس‌ها `Up` یا `Up (healthy)`؛ `migrate` باید `Exited (0)` باشه (یعنی یک‌بار
اجرا شده و موفق تموم شده — این طبیعیه، نه خطا).

### تأیید ساخته‌شدن واقعی volumeهای پایدار (Postgres + Redis)

```bash
docker volume ls
```
چون نام پروژه‌ی Compose `green-vita-bot`ه (خط `name:` بالای `docker-compose.yml`)، دنبال
این دو خط بگرد:
```
local     green-vita-bot_pgdata
local     green-vita-bot_redisdata
```
اگه `green-vita-bot_redisdata` رو ندیدی، یعنی Redis بدون volume پایدار بالا اومده و با
هر بار recreate شدن کانتینر، state مکالمه‌های در حال انجام پاک می‌شه — قبل از ادامه برگرد
و `docker compose config` (بخش ۸.۰) رو دوباره چک کن.

## ۱۱. مشاهده‌ی لاگ‌ها

```bash
docker compose logs -f              # همه، زنده
docker compose logs -f bot          # فقط بات
docker compose logs -f admin        # فقط پنل
docker compose logs bot --tail=100  # ۱۰۰ خط آخر بدون follow
```

---

## ۱۲. تست بات تلگرام

```bash
docker compose logs bot --tail=50
# نباید ai_provider_misconfigured یا ConfigurationError ببینی
```
بعد تو تلگرام:
1. `/start` → پیام خوش‌آمد + کیبورد اصلی
2. یه عکس گیاه بفرست → سؤال «اسم گیاه چیه؟»
3. جواب بده → نتیجه‌ی ۱-تشخیص ← ۲-علت ← ۳-درمان
4. دکمه‌ی «📞 درخواست ویزیت متخصص» → پیام به `BOT_ADMIN_IDS` برسه

## ۱۳. تست پنل مدیریت

چون پنل هنوز auth نداره، **مستقیم پورت ۸۰۰۰ رو عمومی باز نکن.** به‌جاش از SSH tunnel استفاده کن:

```bash
# از کامپیوتر خودت (نه از داخل سرور):
ssh -L 8000:localhost:8000 root@<IP-سرور>
```
بعد تو مرورگر خودت `http://localhost:8000/health` و `http://localhost:8000/` رو باز کن.
انتظار از `/health`: `{"status":"ok"}` — از `/health/ready`: `"database": "ok"`.

---

## ۱۴. روال ری‌استارت سرویس‌ها

```bash
docker compose restart bot      # فقط بات
docker compose restart admin    # فقط پنل
docker compose restart          # همه

# بعد از تغییر .env، برای اطمینان کامل (نه فقط restart):
docker compose up -d
```

## ۱۵. روال بعد از ریبوت سرور

هیچ اقدام دستی لازم نیست **اگه** `systemctl enable docker` رو مرحله‌ی ۴ زده باشی — Docker
daemon خودش با بوت سرور بالا میاد، و کانتینرهای `restart: unless-stopped` خودکار اجرا می‌شن.

بررسی بعد از ریبوت:
```bash
docker compose ps
docker compose logs bot --tail=20
```

---

## ۱۶. روال Backup

**فقط Postgres نیاز به backup داره** (Redis فقط state موقته، دیتای دائمی نداره):

```bash
# بکاپ دستی
docker compose exec db pg_dump -U greenvita greenvita > backup_$(date +%Y%m%d_%H%M%S).sql

# پیشنهاد: یه cron job روزانه
crontab -e
# این خط رو اضافه کن (هر روز ساعت ۳ صبح):
0 3 * * * cd /root/green-vita-bot && docker compose exec -T db pg_dump -U greenvita greenvita > /root/backups/backup_$(date +\%Y\%m\%d).sql
```
بکاپ‌ها رو دوره‌ای به یه جای دیگه (نه خودِ همون سرور) منتقل کن — مثلاً با `scp` به کامپیوتر
خودت یا یه object storage.

## ۱۷. روال Rollback

```bash
cd /root/green-vita-bot
docker compose down
git fetch --all
git checkout 09236f09ca2289cbf1c8dfa626b2f492ef72daed   # نسخه‌ای که این راهنما دیپلویش می‌کنه
# برای برگشت به یه commit دیگه (نه این نسخه)، هش دقیقش رو با `git log --oneline` پیدا کن —
# هیچ‌وقت به‌جاش از تگ v0.1-baseline استفاده نکن؛ اون فاقد پشتیبانی AvalAI و redisdata است.
docker compose up -d --build
```

بازگردانی دیتابیس از بکاپ (فقط در صورت نیاز واقعی):
```bash
cat backup_YYYYMMDD_HHMMSS.sql | docker compose exec -T db psql -U greenvita greenvita
```

---

## ۱۸. چک‌لیست امنیتی نهایی

| الزام | وضعیت بعد از این راهنما |
|---|---|
| ۱. Postgres غیرقابل‌دسترس عمومی | ✅ با قانون `DOCKER-USER` (بخش ۵) |
| ۲. Redis غیرقابل‌دسترس عمومی | ✅ با قانون `DOCKER-USER` (بخش ۵) |
| ۳. فقط پورت لازم عمومی | ✅ فقط ۲۲ (محدود) و ۸۰۰۰ (اختیاری/محدود به IP، ترجیحاً حتی اونم بسته و از tunnel استفاده کن) |
| ۴. SSH محدود | ✅ فقط کلید، بدون رمز (بخش ۵) |
| ۵. Secret تو Git نیست | ✅ `.env` هیچ‌جا commit نمی‌شه (بخش ۷) |
| ۶. `.env` خارج از Git | ✅ در `.gitignore` از قبل هست، با `git check-ignore` تأیید کن |
| ۷. ارتباط سرویس‌ها فقط داخل شبکه‌ی Docker | ✅ از قبل در معماری compose برقراره |
| ۸. Volume پایدار Postgres + Redis | ✅ هر دو — `pgdata` و `redisdata` (`docker volume ls`، بخش ۱۰) |
| ۹. بات خودکار ری‌استارت بعد از کرش/ریبوت | ✅ `restart: unless-stopped` + `systemctl enable docker` |
| ۱۰. پنل خودکار ری‌استارت بعد از کرش/ریبوت | ✅ همان بالا |

---

## ۱۹. توالی دقیق دستورات (برای اجرای واقعی روی VPS)

```bash
# --- نصب پایه ---
apt-get update
apt-get install -y ca-certificates curl gnupg git ufw fail2ban
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker && systemctl start docker

# --- swap ---
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# --- فایروال ---
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw enable
apt-get install -y iptables-persistent

PUB_IF=$(ip -o -4 route show to default | awk '{print $5}')
echo "اینترفیس عمومی: $PUB_IF"
iptables -I DOCKER-USER -i "$PUB_IF" -p tcp --dport 5432 -j DROP
iptables -I DOCKER-USER -i "$PUB_IF" -p tcp --dport 6379 -j DROP
netfilter-persistent save
iptables -L DOCKER-USER -n --line-numbers   # ← باید دو خط DROP برای dpt:5432 و dpt:6379 روی $PUB_IF ببینی؛ اگه ندیدی متوقف شو

# --- SSH سخت‌سازی (بعد از تست موفق کلید SSH) ---
sed -i 's/#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd

# --- کد ---
cd /root
git clone <آدرس-ریپازیتوری-تو> green-vita-bot
cd green-vita-bot
git checkout 09236f09ca2289cbf1c8dfa626b2f492ef72daed   # نه v0.1-baseline — اون تگ ناقصه

# --- env ---
cp .env.example .env
chmod 600 .env
nano .env   # ← پر کردن دستی مقادیر واقعی، سپس ذخیره و خروج
git check-ignore -v .env   # ← تأیید اینکه .env نادیده گرفته می‌شه

# --- اعتبارسنجی Compose (اجباری، قبل از هر up/run) ---
docker compose config   # ← اگه خطا داد متوقف شو، ادامه نده

# --- دیتابیس و مایگریشن ---
docker compose up -d db redis
docker compose logs db --tail=20
docker compose run --rm migrate
docker compose logs migrate

# --- بالا آوردن کامل ---
docker compose up -d --build
docker compose ps
docker volume ls   # ← باید green-vita-bot_pgdata و green-vita-bot_redisdata رو ببینی
docker compose logs bot --tail=50
docker compose logs admin --tail=50

# --- ساخت ادمین اولیه ---
docker compose run --rm bot python -m scripts.seed

# --- تست ---
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
# سپس تو تلگرام: /start و ارسال یک عکس گیاه
```
