--
-- PostgreSQL database dump
--

\restrict r9XKGM3P5cIdXbAOGb86cP77gDruMBofGwrae22cs0dxw2T6WX80h0qfPE4WC87

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: diagnosisseverity; Type: TYPE; Schema: public; Owner: greenvita
--

CREATE TYPE public.diagnosisseverity AS ENUM (
    'none',
    'mild',
    'moderate',
    'severe',
    'unknown'
);


ALTER TYPE public.diagnosisseverity OWNER TO greenvita;

--
-- Name: difficultylevel; Type: TYPE; Schema: public; Owner: greenvita
--

CREATE TYPE public.difficultylevel AS ENUM (
    'easy',
    'medium',
    'hard',
    'unknown'
);


ALTER TYPE public.difficultylevel OWNER TO greenvita;

--
-- Name: messagerole; Type: TYPE; Schema: public; Owner: greenvita
--

CREATE TYPE public.messagerole AS ENUM (
    'user',
    'assistant',
    'system'
);


ALTER TYPE public.messagerole OWNER TO greenvita;

--
-- Name: planthealthstatus; Type: TYPE; Schema: public; Owner: greenvita
--

CREATE TYPE public.planthealthstatus AS ENUM (
    'healthy',
    'sick',
    'under_treatment',
    'recovered',
    'unknown'
);


ALTER TYPE public.planthealthstatus OWNER TO greenvita;

--
-- Name: remindertype; Type: TYPE; Schema: public; Owner: greenvita
--

CREATE TYPE public.remindertype AS ENUM (
    'watering',
    'fertilizing',
    'other'
);


ALTER TYPE public.remindertype OWNER TO greenvita;

--
-- Name: visitstatus; Type: TYPE; Schema: public; Owner: greenvita
--

CREATE TYPE public.visitstatus AS ENUM (
    'pending',
    'scheduled',
    'completed',
    'cancelled',
    'reviewing',
    'confirmed',
    'in_progress'
);


ALTER TYPE public.visitstatus OWNER TO greenvita;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: greenvita
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO greenvita;

--
-- Name: conversations; Type: TABLE; Schema: public; Owner: greenvita
--

CREATE TABLE public.conversations (
    id integer NOT NULL,
    user_id integer NOT NULL,
    plant_id integer,
    role public.messagerole NOT NULL,
    content text NOT NULL,
    ai_provider character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.conversations OWNER TO greenvita;

--
-- Name: conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: greenvita
--

CREATE SEQUENCE public.conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.conversations_id_seq OWNER TO greenvita;

--
-- Name: conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: greenvita
--

ALTER SEQUENCE public.conversations_id_seq OWNED BY public.conversations.id;


--
-- Name: diagnoses; Type: TABLE; Schema: public; Owner: greenvita
--

CREATE TABLE public.diagnoses (
    id integer NOT NULL,
    user_id integer NOT NULL,
    plant_id integer,
    telegram_file_id character varying(255) NOT NULL,
    is_healthy boolean DEFAULT false NOT NULL,
    disease_name character varying(255) DEFAULT 'نامشخص'::character varying NOT NULL,
    severity public.diagnosisseverity DEFAULT 'unknown'::public.diagnosisseverity NOT NULL,
    confidence integer DEFAULT 0 NOT NULL,
    symptoms text,
    treatment text,
    prevention text,
    ai_provider character varying(32) NOT NULL,
    raw_response text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    plant_name_input character varying(255),
    user_notes text,
    expert_visit_requested boolean DEFAULT false NOT NULL,
    cause text,
    visit_status public.visitstatus DEFAULT 'pending'::public.visitstatus NOT NULL,
    visit_scheduled_at timestamp with time zone,
    admin_notes text
);


ALTER TABLE public.diagnoses OWNER TO greenvita;

--
-- Name: diagnoses_id_seq; Type: SEQUENCE; Schema: public; Owner: greenvita
--

CREATE SEQUENCE public.diagnoses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.diagnoses_id_seq OWNER TO greenvita;

--
-- Name: diagnoses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: greenvita
--

ALTER SEQUENCE public.diagnoses_id_seq OWNED BY public.diagnoses.id;


--
-- Name: plant_identifications; Type: TABLE; Schema: public; Owner: greenvita
--

CREATE TABLE public.plant_identifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    telegram_file_id character varying(255) NOT NULL,
    persian_name character varying(255) DEFAULT 'نامشخص'::character varying NOT NULL,
    scientific_name character varying(255),
    confidence integer DEFAULT 0 NOT NULL,
    difficulty_level public.difficultylevel DEFAULT 'unknown'::public.difficultylevel NOT NULL,
    light_requirement text,
    watering_schedule text,
    humidity text,
    temperature text,
    soil_mix text,
    fertilizer_recommendation text,
    potting_advice text,
    repotting_interval text,
    propagation_methods text,
    common_pests text,
    common_diseases text,
    toxicity_pets text,
    toxicity_humans text,
    preventive_care_tips text,
    ai_provider character varying(32) NOT NULL,
    raw_response text,
    expert_visit_requested boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    visit_status public.visitstatus DEFAULT 'pending'::public.visitstatus NOT NULL,
    visit_scheduled_at timestamp with time zone,
    admin_notes text
);


ALTER TABLE public.plant_identifications OWNER TO greenvita;

--
-- Name: plant_identifications_id_seq; Type: SEQUENCE; Schema: public; Owner: greenvita
--

CREATE SEQUENCE public.plant_identifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.plant_identifications_id_seq OWNER TO greenvita;

--
-- Name: plant_identifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: greenvita
--

ALTER SEQUENCE public.plant_identifications_id_seq OWNED BY public.plant_identifications.id;


--
-- Name: plants; Type: TABLE; Schema: public; Owner: greenvita
--

CREATE TABLE public.plants (
    id integer NOT NULL,
    owner_id integer NOT NULL,
    name character varying(255) NOT NULL,
    species character varying(255),
    notes text,
    health_status public.planthealthstatus DEFAULT 'unknown'::public.planthealthstatus NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.plants OWNER TO greenvita;

--
-- Name: plants_id_seq; Type: SEQUENCE; Schema: public; Owner: greenvita
--

CREATE SEQUENCE public.plants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.plants_id_seq OWNER TO greenvita;

--
-- Name: plants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: greenvita
--

ALTER SEQUENCE public.plants_id_seq OWNED BY public.plants.id;


--
-- Name: reminders; Type: TABLE; Schema: public; Owner: greenvita
--

CREATE TABLE public.reminders (
    id integer NOT NULL,
    user_id integer NOT NULL,
    plant_id integer NOT NULL,
    reminder_type public.remindertype NOT NULL,
    interval_days integer DEFAULT 7 NOT NULL,
    next_run_at timestamp with time zone NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reminders OWNER TO greenvita;

--
-- Name: reminders_id_seq; Type: SEQUENCE; Schema: public; Owner: greenvita
--

CREATE SEQUENCE public.reminders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reminders_id_seq OWNER TO greenvita;

--
-- Name: reminders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: greenvita
--

ALTER SEQUENCE public.reminders_id_seq OWNED BY public.reminders.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: greenvita
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(255),
    first_name character varying(255),
    last_name character varying(255),
    phone_number character varying(32),
    language_code character varying(8),
    is_admin boolean DEFAULT false NOT NULL,
    is_blocked boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO greenvita;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: greenvita
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO greenvita;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: greenvita
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: conversations id; Type: DEFAULT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.conversations ALTER COLUMN id SET DEFAULT nextval('public.conversations_id_seq'::regclass);


--
-- Name: diagnoses id; Type: DEFAULT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.diagnoses ALTER COLUMN id SET DEFAULT nextval('public.diagnoses_id_seq'::regclass);


--
-- Name: plant_identifications id; Type: DEFAULT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.plant_identifications ALTER COLUMN id SET DEFAULT nextval('public.plant_identifications_id_seq'::regclass);


--
-- Name: plants id; Type: DEFAULT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.plants ALTER COLUMN id SET DEFAULT nextval('public.plants_id_seq'::regclass);


--
-- Name: reminders id; Type: DEFAULT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.reminders ALTER COLUMN id SET DEFAULT nextval('public.reminders_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: greenvita
--

COPY public.alembic_version (version_num) FROM stdin;
0007
\.


--
-- Data for Name: conversations; Type: TABLE DATA; Schema: public; Owner: greenvita
--

COPY public.conversations (id, user_id, plant_id, role, content, ai_provider, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: diagnoses; Type: TABLE DATA; Schema: public; Owner: greenvita
--

COPY public.diagnoses (id, user_id, plant_id, telegram_file_id, is_healthy, disease_name, severity, confidence, symptoms, treatment, prevention, ai_provider, raw_response, created_at, updated_at, plant_name_input, user_notes, expert_visit_requested, cause, visit_status, visit_scheduled_at, admin_notes) FROM stdin;
1	1	\N	AgACAgQAAxkBAAMIan9GOAye7TWMh_-gg8oJGjM8orIAAogPaxv0_vlTX0nEyQJI3h8BAAMCAAN4AAM9BA	f	سوختگی خفیف نوک برگ‌ها	mild	78	گیاه در کل سبز و زنده به نظر می‌رسد\nنوک بعضی برگ‌ها خشک و قهوه‌ای شده است\nبرگ‌ها کمی آویزان و باریک هستند اما نشانه واضح پوسیدگی یا آفت دیده نمی‌شود	1. برگ‌های کاملاً خشک یا نوک‌های قهوه‌ای را با قیچی تمیز فقط از قسمت خشک‌شده کوتاه کنید. 2. قبل از آبیاری، خاک را تا چند سانتی‌متر عمق بررسی کنید؛ فقط وقتی خاک کاملاً خشک شد آبیاری کنید. 3. بعد از آبیاری، آب جمع‌شده در زیرگلدانی را حتماً خالی کنید. 4. گلدان را در نور زیاد ولی غیرمستقیم قرار دهید؛ چند ساعت آفتاب ملایم صبحگاهی هم مناسب است. 5. اگر خاک خیلی فشرده یا همیشه مرطوب می‌ماند، در فصل مناسب آن را با خاک سبک و دارای زهکشی خوب تعویض کنید. 6. فعلاً کوددهی نکنید تا رشد گیاه پایدار شود.	از آبیاری زیاد و باقی ماندن آب در زیرگلدانی جلوگیری کنید. از گلدان دارای سوراخ زهکشی استفاده کنید. هر بار فقط بعد از خشک شدن خاک آبیاری کنید و در صورت امکان از آب بدون املاح زیاد یا آب مانده ۲۴ ساعته استفاده کنید. گیاه را در محل پرنور نگه دارید و ماهی یک‌بار برگ‌ها را از نظر آفت و خشکی نوک بررسی کنید.	openai	{"is_healthy":false,"disease_name":"سوختگی خفیف نوک برگ‌ها","severity":"mild","confidence":78,"symptoms":["گیاه در کل سبز و زنده به نظر می‌رسد","نوک بعضی برگ‌ها خشک و قهوه‌ای شده است","برگ‌ها کمی آویزان و باریک هستند اما نشانه واضح پوسیدگی یا آفت دیده نمی‌شود"],"cause":"احتمالاً به دلیل آبیاری نامنظم، ماندن آب در زیرگلدانی، خشکی زیاد هوا یا تجمع املاح آب در خاک، نوک برگ‌ها دچار سوختگی شده است. این گیاه شبیه نخل دم‌اسبی است و به آبیاری زیاد حساس است.","treatment":"1. برگ‌های کاملاً خشک یا نوک‌های قهوه‌ای را با قیچی تمیز فقط از قسمت خشک‌شده کوتاه کنید. 2. قبل از آبیاری، خاک را تا چند سانتی‌متر عمق بررسی کنید؛ فقط وقتی خاک کاملاً خشک شد آبیاری کنید. 3. بعد از آبیاری، آب جمع‌شده در زیرگلدانی را حتماً خالی کنید. 4. گلدان را در نور زیاد ولی غیرمستقیم قرار دهید؛ چند ساعت آفتاب ملایم صبحگاهی هم مناسب است. 5. اگر خاک خیلی فشرده یا همیشه مرطوب می‌ماند، در فصل مناسب آن را با خاک سبک و دارای زهکشی خوب تعویض کنید. 6. فعلاً کوددهی نکنید تا رشد گیاه پایدار شود.","prevention":"از آبیاری زیاد و باقی ماندن آب در زیرگلدانی جلوگیری کنید. از گلدان دارای سوراخ زهکشی استفاده کنید. هر بار فقط بعد از خشک شدن خاک آبیاری کنید و در صورت امکان از آب بدون املاح زیاد یا آب مانده ۲۴ ساعته استفاده کنید. گیاه را در محل پرنور نگه دارید و ماهی یک‌بار برگ‌ها را از نظر آفت و خشکی نوک بررسی کنید."}	2026-08-14 19:25:55.343929+00	2026-08-14 19:25:55.343929+00	\N	\N	f	احتمالاً به دلیل آبیاری نامنظم، ماندن آب در زیرگلدانی، خشکی زیاد هوا یا تجمع املاح آب در خاک، نوک برگ‌ها دچار سوختگی شده است. این گیاه شبیه نخل دم‌اسبی است و به آبیاری زیاد حساس است.	pending	\N	\N
7	1	\N	AgACAgQAAxkBAAOfaoHtD5xTMf7iLHsjko2PobfVS54AAlQPaxu0gRFQavrIVO5pWfMBAAMCAAN4AAM9BA	f	نامشخص	unknown	0	\N	پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.	\N	openai		2026-08-16 20:52:20.563765+00	2026-08-16 20:52:20.563765+00	نه	\N	f	\N	pending	\N	\N
8	1	\N	AgACAgQAAxkBAAOfaoHtD5xTMf7iLHsjko2PobfVS54AAlQPaxu0gRFQavrIVO5pWfMBAAMCAAN4AAM9BA	f	نامشخص	unknown	0	\N	پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.	\N	openai		2026-08-16 20:47:31.420804+00	2026-08-16 20:47:31.420804+00	نه	\N	f	\N	pending	\N	\N
9	1	\N	AgACAgQAAxkBAAPyaoR_FVboPyDh8da6Coe8kjYKK5wAAn0QaxuNLSBQ3lzasz7xLXQBAAMCAAN4AAM9BA	f	نامشخص	unknown	0	\N	پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.	\N	openai		2026-08-18 15:49:44.927122+00	2026-08-18 15:49:44.927122+00	نه	\N	f	\N	pending	\N	\N
10	1	\N	AgACAgQAAxkBAAP2aoR_a4uXF-zgVdI0bWMwsXbWkF8AAn4QaxuNLSBQch9JN1pXC6cBAAMCAAN5AAM9BA	f	نامشخص	unknown	0	\N	پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.	\N	openai		2026-08-18 15:51:15.462131+00	2026-08-18 15:51:15.462131+00	نه	\N	f	\N	pending	\N	\N
2	1	\N	AgACAgQAAxkBAAMIan9GOAye7TWMh_-gg8oJGjM8orIAAogPaxv0_vlTX0nEyQJI3h8BAAMCAAN4AAM9BA	f	خشکی نوک برگ و تنش آبی خفیف	mild	78	خشک و قهوه‌ای شدن نوک بعضی برگ‌ها\nآویزان شدن بخشی از برگ‌های باریک\nبدنه پیازی گیاه سالم و بدون پوسیدگی واضح دیده می‌شود	1. برگ‌های کاملاً خشک یا نوک‌های قهوه‌ای را با قیچی تمیز فقط از قسمت خشک کوتاه کنید. 2. قبل از آبیاری، خاک را تا عمق چند سانتی‌متری بررسی کنید؛ فقط وقتی خاک کاملاً خشک شد آبیاری کنید. 3. هنگام آبیاری، آن‌قدر آب بدهید که از زیر گلدان خارج شود و سپس آب زیرگلدانی را خالی کنید. 4. گیاه را در نور زیاد ولی غیرمستقیم، کنار پنجره روشن قرار دهید. 5. اگر خاک خیلی سنگین یا همیشه مرطوب می‌ماند، در فصل مناسب آن را با خاک سبک و زهکش‌دار مثل ترکیب خاک کاکتوس، پرلیت و کمی خاک برگ تعویض کنید. 6. فعلاً کوددهی زیاد انجام ندهید؛ در فصل رشد ماهی یک‌بار کود رقیق کافی است.	برای جلوگیری از تکرار، آبیاری را کم و عمیق انجام دهید، اجازه دهید خاک بین دو آبیاری خشک شود، گلدان حتماً سوراخ زهکش داشته باشد، گیاه را در نور زیاد نگه دارید و هر چند وقت یک‌بار خاک را با آبیاری کامل شست‌وشو دهید تا املاح اضافی جمع نشود.	openai	{\n  "is_healthy": false,\n  "disease_name": "خشکی نوک برگ و تنش آبی خفیف",\n  "severity": "mild",\n  "confidence": 78,\n  "symptoms": [\n    "خشک و قهوه‌ای شدن نوک بعضی برگ‌ها",\n    "آویزان شدن بخشی از برگ‌های باریک",\n    "بدنه پیازی گیاه سالم و بدون پوسیدگی واضح دیده می‌شود"\n  ],\n  "cause": "این گیاه احتمالاً لیندا یا نخل دم‌اسبی است و مشکل اصلی بیشتر به آبیاری نامنظم، خشکی زیاد هوا، نور کم یا تجمع املاح در خاک مربوط است. این گیاه به آبیاری زیاد حساس است و اگر خاک دیر خشک شود، خطر پوسیدگی ریشه هم وجود دارد.",\n  "treatment": "1. برگ‌های کاملاً خشک یا نوک‌های قهوه‌ای را با قیچی تمیز فقط از قسمت خشک کوتاه کنید. 2. قبل از آبیاری، خاک را تا عمق چند سانتی‌متری بررسی کنید؛ فقط وقتی خاک کاملاً خشک شد آبیاری کنید. 3. هنگام آبیاری، آن‌قدر آب بدهید که از زیر گلدان خارج شود و سپس آب زیرگلدانی را خالی کنید. 4. گیاه را در نور زیاد ولی غیرمستقیم، کنار پنجره روشن قرار دهید. 5. اگر خاک خیلی سنگین یا همیشه مرطوب می‌ماند، در فصل مناسب آن را با خاک سبک و زهکش‌دار مثل ترکیب خاک کاکتوس، پرلیت و کمی خاک برگ تعویض کنید. 6. فعلاً کوددهی زیاد انجام ندهید؛ در فصل رشد ماهی یک‌بار کود رقیق کافی است.",\n  "prevention": "برای جلوگیری از تکرار، آبیاری را کم و عمیق انجام دهید، اجازه دهید خاک بین دو آبیاری خشک شود، گلدان حتماً سوراخ زهکش داشته باشد، گیاه را در نور زیاد نگه دارید و هر چند وقت یک‌بار خاک را با آبیاری کامل شست‌وشو دهید تا املاح اضافی جمع نشود."\n}	2026-08-14 19:26:18.099194+00	2026-08-16 16:38:38.923408+00	نمی دونم	\N	t	این گیاه احتمالاً لیندا یا نخل دم‌اسبی است و مشکل اصلی بیشتر به آبیاری نامنظم، خشکی زیاد هوا، نور کم یا تجمع املاح در خاک مربوط است. این گیاه به آبیاری زیاد حساس است و اگر خاک دیر خشک شود، خطر پوسیدگی ریشه هم وجود دارد.	pending	\N	\N
5	1	\N	AgACAgQAAxkBAANean_4Iz16cWhorihTaRzrYi_T12wAAooPaxv0_vlTS6d6fYmKEDwBAAMCAAN5AAM9BA	f	لکه برگی خفیف و سوختگی نوک برگ	mild	72	وجود لکه‌های کوچک قهوه‌ای و تیره روی سطح برگ\nخشکیدگی و قهوه‌ای شدن نوک برگ\nزردی بسیار خفیف در بخش پایینی برگ\nبافت کلی برگ هنوز سبز و نسبتاً سالم است	1. این برگ را فعلاً جدا نکنید مگر لکه‌ها زیادتر شوند؛ فقط قسمت کاملاً خشک نوک برگ را با قیچی ضدعفونی‌شده ببرید. 2. برگ‌ها را با دستمال نرم و کمی مرطوب تمیز کنید و بعد خشک نگه دارید. 3. آبیاری را فقط وقتی انجام دهید که 2 تا 3 سانتی‌متر سطح خاک خشک شده باشد. 4. از اسپری آب روی برگ‌ها خودداری کنید، مخصوصاً اگر هوا جریان ندارد. 5. گیاه را در نور زیاد ولی غیرمستقیم قرار دهید. 6. اگر لکه‌ها طی 7 تا 10 روز بیشتر شدند، برگ‌های خیلی آلوده را حذف کنید و از قارچ‌کش ملایم مثل مانکوزب یا قارچ‌کش مسی طبق دستور روی بسته استفاده کنید.	بین دو آبیاری اجازه دهید سطح خاک کمی خشک شود، آب زیرگلدانی را خالی کنید، گیاه را در محیط با تهویه بهتر و نور غیرمستقیم نگه دارید، برگ‌ها را خیس نکنید و هر چند هفته یک‌بار پشت و روی برگ‌ها را برای لکه یا آفت بررسی کنید.	openai	{\n  "is_healthy": false,\n  "disease_name": "لکه برگی خفیف و سوختگی نوک برگ",\n  "severity": "mild",\n  "confidence": 72,\n  "symptoms": [\n    "وجود لکه‌های کوچک قهوه‌ای و تیره روی سطح برگ",\n    "خشکیدگی و قهوه‌ای شدن نوک برگ",\n    "زردی بسیار خفیف در بخش پایینی برگ",\n    "بافت کلی برگ هنوز سبز و نسبتاً سالم است"\n  ],\n  "cause": "احتمالاً رطوبت زیاد روی برگ، تهویه ضعیف یا آبیاری بیش از حد باعث شروع لکه‌های قارچی خفیف شده است. سوختگی نوک برگ هم می‌تواند از آبیاری نامنظم، تجمع املاح آب یا خشکی مقطعی خاک ایجاد شده باشد.",\n  "treatment": "1. این برگ را فعلاً جدا نکنید مگر لکه‌ها زیادتر شوند؛ فقط قسمت کاملاً خشک نوک برگ را با قیچی ضدعفونی‌شده ببرید. 2. برگ‌ها را با دستمال نرم و کمی مرطوب تمیز کنید و بعد خشک نگه دارید. 3. آبیاری را فقط وقتی انجام دهید که 2 تا 3 سانتی‌متر سطح خاک خشک شده باشد. 4. از اسپری آب روی برگ‌ها خودداری کنید، مخصوصاً اگر هوا جریان ندارد. 5. گیاه را در نور زیاد ولی غیرمستقیم قرار دهید. 6. اگر لکه‌ها طی 7 تا 10 روز بیشتر شدند، برگ‌های خیلی آلوده را حذف کنید و از قارچ‌کش ملایم مثل مانکوزب یا قارچ‌کش مسی طبق دستور روی بسته استفاده کنید.",\n  "prevention": "بین دو آبیاری اجازه دهید سطح خاک کمی خشک شود، آب زیرگلدانی را خالی کنید، گیاه را در محیط با تهویه بهتر و نور غیرمستقیم نگه دارید، برگ‌ها را خیس نکنید و هر چند هفته یک‌بار پشت و روی برگ‌ها را برای لکه یا آفت بررسی کنید."\n}	2026-08-15 05:25:01.159837+00	2026-08-15 05:25:01.159837+00	نه	\N	f	احتمالاً رطوبت زیاد روی برگ، تهویه ضعیف یا آبیاری بیش از حد باعث شروع لکه‌های قارچی خفیف شده است. سوختگی نوک برگ هم می‌تواند از آبیاری نامنظم، تجمع املاح آب یا خشکی مقطعی خاک ایجاد شده باشد.	pending	\N	\N
6	1	\N	AgACAgQAAxkBAANaan_3s2yEZO1-ZmesqhJ8sGs-5OIAAmIPaxv0_gFQOs72ZmzjFtwBAAMCAAN5AAM9BA	f	تصویر نامشخص یا نامرتبط	none	100	تصویر ارسالی نقاشی یا تصویر کارتونی است و عکس واقعی از گیاه نیست\nجزئیات واقعی برگ، ساقه، خاک و علائم بیماری قابل بررسی نیست	لطفاً یک عکس واقعی و واضح از گیاه بفرستید: 1) از کل گیاه در نور طبیعی عکس بگیرید. 2) از برگ‌های مشکوک از نزدیک عکس بگیرید. 3) سطح خاک و گلدان را هم نشان دهید. 4) اگر لکه، زردی، خشکی، حشره یا پوسیدگی وجود دارد، همان قسمت را واضح و نزدیک ثبت کنید.	برای بررسی دقیق در آینده، عکس را در نور کافی، بدون فیلتر و از چند زاویه بفرستید و اطلاعاتی مثل میزان آبیاری، نور محل نگهداری و مدت زمان بروز علائم را هم ذکر کنید.	openai	{"is_healthy":false,"disease_name":"تصویر نامشخص یا نامرتبط","severity":"none","confidence":100,"symptoms":["تصویر ارسالی نقاشی یا تصویر کارتونی است و عکس واقعی از گیاه نیست","جزئیات واقعی برگ، ساقه، خاک و علائم بیماری قابل بررسی نیست"],"cause":"به دلیل واقعی نبودن تصویر و نبود جزئیات کافی، امکان تشخیص سلامت، بیماری، آفت یا کمبود غذایی گیاه وجود ندارد.","treatment":"لطفاً یک عکس واقعی و واضح از گیاه بفرستید: 1) از کل گیاه در نور طبیعی عکس بگیرید. 2) از برگ‌های مشکوک از نزدیک عکس بگیرید. 3) سطح خاک و گلدان را هم نشان دهید. 4) اگر لکه، زردی، خشکی، حشره یا پوسیدگی وجود دارد، همان قسمت را واضح و نزدیک ثبت کنید.","prevention":"برای بررسی دقیق در آینده، عکس را در نور کافی، بدون فیلتر و از چند زاویه بفرستید و اطلاعاتی مثل میزان آبیاری، نور محل نگهداری و مدت زمان بروز علائم را هم ذکر کنید."}	2026-08-15 05:23:04.399222+00	2026-08-15 05:23:04.399222+00	نه	\N	f	به دلیل واقعی نبودن تصویر و نبود جزئیات کافی، امکان تشخیص سلامت، بیماری، آفت یا کمبود غذایی گیاه وجود ندارد.	pending	\N	\N
3	1	\N	AgACAgQAAxkBAAMOan9GqChMpx5TAvLPsljDGr_WjlYAAokPaxv0_vlTAWc_Q9djO1ABAAMCAAN5AAM9BA	f	استرس نوری و آبیاری نامناسب	mild	78	برگ‌های کوچک کنار ساقه‌ها در بعضی قسمت‌ها زرد و خشک شده‌اند\nرشد گیاه کمی کشیده و متمایل به سمت نور دیده می‌شود\nبخش‌هایی از برگ‌ها قهوه‌ای و خشک هستند\nساقه‌ها هنوز سبز و نسبتاً محکم به نظر می‌رسند و نشانه واضح پوسیدگی شدید دیده نمی‌شود	1. گیاه را به محل بسیار روشن‌تر منتقل کن؛ کنار پنجره پرنور با نور فیلترشده مناسب است. جابه‌جایی را طی 7 تا 10 روز تدریجی انجام بده تا دچار آفتاب‌سوختگی نشود. 2. برگ‌های کاملاً خشک و زرد را با دستکش جدا کن؛ شیره سفید افوربیا سمی و محرک پوست است، پس با پوست و چشم تماس نداشته باشد. 3. قبل از آبیاری، خاک را بررسی کن؛ فقط وقتی حداقل نصف تا دو سوم عمق خاک کاملاً خشک شد آبیاری کن. 4. هنگام آبیاری، کامل آب بده تا از زهکش خارج شود، سپس آب زیرگلدانی را خالی کن. 5. اگر گلدان زهکش ندارد یا خاک سنگین است، در فصل رشد گیاه را به خاک کاکتوس با زهکشی بالا منتقل کن؛ ترکیب خاک کاکتوس به همراه پرلیت یا پوکه مناسب است. 6. اگر قسمت‌هایی از ساقه نرم، سیاه یا بوی بددار شد، آبیاری را قطع کن و همان بخش‌ها را بررسی و حذف کن چون می‌تواند نشانه پوسیدگی باشد.	گیاه را همیشه در نور زیاد نگه دار، از آبیاری برنامه‌ای و زیاد خودداری کن، اجازه بده خاک بین دو آبیاری خشک شود، آب زیرگلدانی را باقی نگذار، و هر ماه ساقه‌ها را از نظر نرمی، لکه سیاه یا آفت بررسی کن.	openai	{"is_healthy":false,"disease_name":"استرس نوری و آبیاری نامناسب","severity":"mild","confidence":78,"symptoms":["برگ‌های کوچک کنار ساقه‌ها در بعضی قسمت‌ها زرد و خشک شده‌اند","رشد گیاه کمی کشیده و متمایل به سمت نور دیده می‌شود","بخش‌هایی از برگ‌ها قهوه‌ای و خشک هستند","ساقه‌ها هنوز سبز و نسبتاً محکم به نظر می‌رسند و نشانه واضح پوسیدگی شدید دیده نمی‌شود"],"cause":"افوربیا تریگونا به نور زیاد و غیرمستقیم تا چند ساعت نور ملایم مستقیم نیاز دارد. قرار گرفتن در گوشه کم‌نور باعث ریزش و خشکی برگ‌ها و رشد کشیده می‌شود. همچنین اگر خاک مدت طولانی مرطوب بماند یا آب در زیرگلدانی جمع شود، ریشه‌ها تحت فشار قرار می‌گیرند و برگ‌ها زرد یا خشک می‌شوند.","treatment":"1. گیاه را به محل بسیار روشن‌تر منتقل کن؛ کنار پنجره پرنور با نور فیلترشده مناسب است. جابه‌جایی را طی 7 تا 10 روز تدریجی انجام بده تا دچار آفتاب‌سوختگی نشود. 2. برگ‌های کاملاً خشک و زرد را با دستکش جدا کن؛ شیره سفید افوربیا سمی و محرک پوست است، پس با پوست و چشم تماس نداشته باشد. 3. قبل از آبیاری، خاک را بررسی کن؛ فقط وقتی حداقل نصف تا دو سوم عمق خاک کاملاً خشک شد آبیاری کن. 4. هنگام آبیاری، کامل آب بده تا از زهکش خارج شود، سپس آب زیرگلدانی را خالی کن. 5. اگر گلدان زهکش ندارد یا خاک سنگین است، در فصل رشد گیاه را به خاک کاکتوس با زهکشی بالا منتقل کن؛ ترکیب خاک کاکتوس به همراه پرلیت یا پوکه مناسب است. 6. اگر قسمت‌هایی از ساقه نرم، سیاه یا بوی بددار شد، آبیاری را قطع کن و همان بخش‌ها را بررسی و حذف کن چون می‌تواند نشانه پوسیدگی باشد.","prevention":"گیاه را همیشه در نور زیاد نگه دار، از آبیاری برنامه‌ای و زیاد خودداری کن، اجازه بده خاک بین دو آبیاری خشک شود، آب زیرگلدانی را باقی نگذار، و هر ماه ساقه‌ها را از نظر نرمی، لکه سیاه یا آفت بررسی کن."}	2026-08-14 19:29:40.343034+00	2026-08-16 12:22:18.11299+00	افوربیا تریگونا یا درخت شیر آفریقایی	\N	t	افوربیا تریگونا به نور زیاد و غیرمستقیم تا چند ساعت نور ملایم مستقیم نیاز دارد. قرار گرفتن در گوشه کم‌نور باعث ریزش و خشکی برگ‌ها و رشد کشیده می‌شود. همچنین اگر خاک مدت طولانی مرطوب بماند یا آب در زیرگلدانی جمع شود، ریشه‌ها تحت فشار قرار می‌گیرند و برگ‌ها زرد یا خشک می‌شوند.	pending	\N	\N
4	1	\N	AgACAgQAAxkBAANPan_3LIVJXsiOqey2CgS8ONEIlm0AAmEPaxv0_gFQ9lcIoDO9cL0BAAMCAAN5AAM9BA	f	خشکی نوک برگ و تنش آبی دراسنا	moderate	78	خشک و قهوه‌ای شدن نوک و حاشیه برگ‌ها\nکم‌پشت شدن تاج برگ‌ها\nزردی و خشکی تعدادی از برگ‌های پایینی\nظاهر کلی ضعیف و کم‌طراوت گیاه	1. برگ‌های کاملاً خشک و قهوه‌ای را با قیچی تمیز حذف کنید و فقط قسمت‌های سوخته نوک برگ را با حفظ فرم برگ ببُرید. 2. رطوبت خاک را بررسی کنید؛ هر زمان 3 تا 5 سانتی‌متر بالای خاک خشک شد آبیاری انجام دهید. 3. هنگام آبیاری، آب را کامل بدهید تا از کف گلدان خارج شود و آب جمع‌شده در زیرگلدانی را دور بریزید. 4. اگر خاک خیلی سفت، شور یا قدیمی است، 3 تا 5 سانتی‌متر سطح خاک را تعویض کنید یا در صورت امکان در فصل مناسب با خاک سبک و دارای زهکش خوب تعویض گلدان انجام دهید. 5. از آب بدون کلر یا آبی که 24 ساعت مانده استفاده کنید، چون دراسنا به املاح و کلر حساس است. 6. گیاه را در نور زیاد ولی غیرمستقیم قرار دهید و از تابش مستقیم و داغ پشت شیشه دور نگه دارید. 7. تا زمان بهبود، کوددهی را متوقف کنید و بعد از رشد برگ جدید، ماهی یک‌بار با کود کامل رقیق‌شده تغذیه کنید.	برای جلوگیری از تکرار مشکل، برنامه آبیاری را بر اساس خشکی خاک تنظیم کنید نه روز ثابت. از آب کم‌املاح استفاده کنید، زهکشی گلدان را همیشه باز نگه دارید، گیاه را نزدیک باد سرد یا گرمای مستقیم قرار ندهید و هر چند وقت یک‌بار برگ‌ها را از نظر خشکی، آفت و تغییر رنگ بررسی کنید.	openai	{\n  "is_healthy": false,\n  "disease_name": "خشکی نوک برگ و تنش آبی دراسنا",\n  "severity": "moderate",\n  "confidence": 78,\n  "symptoms": [\n    "خشک و قهوه‌ای شدن نوک و حاشیه برگ‌ها",\n    "کم‌پشت شدن تاج برگ‌ها",\n    "زردی و خشکی تعدادی از برگ‌های پایینی",\n    "ظاهر کلی ضعیف و کم‌طراوت گیاه"\n  ],\n  "cause": "احتمالاً گیاه دچار تنش ناشی از آبیاری نامنظم، خشکی هوا و تجمع املاح در خاک شده است. دراسنا به آبیاری زیاد حساس است، اما خشک ماندن طولانی خاک و رطوبت پایین محیط هم باعث سوختگی نوک برگ‌ها و ریزش برگ‌ها می‌شود. نور پشت شیشه اگر خیلی مستقیم یا خیلی کم باشد نیز می‌تواند این مشکل را تشدید کند.",\n  "treatment": "1. برگ‌های کاملاً خشک و قهوه‌ای را با قیچی تمیز حذف کنید و فقط قسمت‌های سوخته نوک برگ را با حفظ فرم برگ ببُرید. 2. رطوبت خاک را بررسی کنید؛ هر زمان 3 تا 5 سانتی‌متر بالای خاک خشک شد آبیاری انجام دهید. 3. هنگام آبیاری، آب را کامل بدهید تا از کف گلدان خارج شود و آب جمع‌شده در زیرگلدانی را دور بریزید. 4. اگر خاک خیلی سفت، شور یا قدیمی است، 3 تا 5 سانتی‌متر سطح خاک را تعویض کنید یا در صورت امکان در فصل مناسب با خاک سبک و دارای زهکش خوب تعویض گلدان انجام دهید. 5. از آب بدون کلر یا آبی که 24 ساعت مانده استفاده کنید، چون دراسنا به املاح و کلر حساس است. 6. گیاه را در نور زیاد ولی غیرمستقیم قرار دهید و از تابش مستقیم و داغ پشت شیشه دور نگه دارید. 7. تا زمان بهبود، کوددهی را متوقف کنید و بعد از رشد برگ جدید، ماهی یک‌بار با کود کامل رقیق‌شده تغذیه کنید.",\n  "prevention": "برای جلوگیری از تکرار مشکل، برنامه آبیاری را بر اساس خشکی خاک تنظیم کنید نه روز ثابت. از آب کم‌املاح استفاده کنید، زهکشی گلدان را همیشه باز نگه دارید، گیاه را نزدیک باد سرد یا گرمای مستقیم قرار ندهید و هر چند وقت یک‌بار برگ‌ها را از نظر خشکی، آفت و تغییر رنگ بررسی کنید."\n}	2026-08-15 05:20:55.837315+00	2026-08-16 16:36:42.152623+00	نه	\N	t	احتمالاً گیاه دچار تنش ناشی از آبیاری نامنظم، خشکی هوا و تجمع املاح در خاک شده است. دراسنا به آبیاری زیاد حساس است، اما خشک ماندن طولانی خاک و رطوبت پایین محیط هم باعث سوختگی نوک برگ‌ها و ریزش برگ‌ها می‌شود. نور پشت شیشه اگر خیلی مستقیم یا خیلی کم باشد نیز می‌تواند این مشکل را تشدید کند.	pending	\N	\N
\.


--
-- Data for Name: plant_identifications; Type: TABLE DATA; Schema: public; Owner: greenvita
--

COPY public.plant_identifications (id, user_id, telegram_file_id, persian_name, scientific_name, confidence, difficulty_level, light_requirement, watering_schedule, humidity, temperature, soil_mix, fertilizer_recommendation, potting_advice, repotting_interval, propagation_methods, common_pests, common_diseases, toxicity_pets, toxicity_humans, preventive_care_tips, ai_provider, raw_response, expert_visit_requested, created_at, updated_at, visit_status, visit_scheduled_at, admin_notes) FROM stdin;
1	1	AgACAgQAAxkBAAMOan9GqChMpx5TAvLPsljDGr_WjlYAAokPaxv0_vlTAWc_Q9djO1ABAAMCAAN5AAM9BA	افوربیا تریگونا یا درخت شیر آفریقایی	Euphorbia trigona	94	easy	نور زیاد و غیرمستقیم؛ کنار پنجره پرنور شرقی یا جنوبی با آفتاب ملایم چند ساعت در روز مناسب است. در گوشه کم‌نور رشدش باریک و برگ‌ها خشک می‌شوند.	فقط وقتی خاک تا عمق زیاد کاملاً خشک شد آبیاری کنید؛ معمولاً بهار و تابستان هر ۲ تا ۳ هفته و پاییز و زمستان هر ۴ تا ۶ هفته. بعد از آبیاری، آب زیرگلدانی را خالی کنید.	رطوبت معمول خانه کافی است؛ به غبارپاشی نیاز ندارد و رطوبت زیاد می‌تواند باعث پوسیدگی ساقه شود.	دمای مناسب ۱۸ تا ۳۰ درجه سانتی‌گراد است. از سرما، باد کولر و دمای زیر ۱۲ درجه دور نگه دارید.	خاک بسیار سبک و زهکش‌دار؛ ترکیب مناسب: خاک کاکتوس به‌همراه پرلیت یا پومیس و کمی ماسه درشت. خاک سنگین و همیشه مرطوب برای این گیاه خطرناک است.	در بهار و تابستان ماهی یک‌بار کود مخصوص کاکتوس و ساکولنت با نصف غلظت استفاده شود. در پاییز و زمستان کوددهی را قطع کنید.	گلدان حتماً سوراخ زهکشی داشته باشد و به‌دلیل قد بلند گیاه، گلدان نسبتاً سنگین و پایدار انتخاب شود. سنگ‌ریزه روی خاک اشکالی ندارد، اما نباید مانع خشک شدن خاک شود.	هر ۲ تا ۳ سال یک‌بار یا زمانی که ریشه‌ها گلدان را پر کردند؛ بهترین زمان تعویض گلدان اوایل بهار است.	قلمه ساقه پس از خشک شدن محل برش به مدت ۳ تا ۷ روز\nقلمه شاخه‌های جانبی و کاشت در خاک خشک و سبک	شپشک آردآلود\nکنه تارعنکبوتی	پوسیدگی ریشه بر اثر آبیاری زیاد\nپوسیدگی و لکه‌های نرم ساقه در رطوبت یا سرمای زیاد	برای گربه و سگ سمی است؛ شیره سفید آن می‌تواند باعث تحریک دهان، استفراغ، سوزش پوست و چشم شود.	شیره سفید گیاه برای پوست و چشم محرک و سوزاننده است؛ هنگام قلمه‌گیری یا جابه‌جایی از دستکش استفاده کنید و آن را دور از دسترس کودکان نگه دارید.	گیاه را به محل پرنورتر منتقل کنید، اما اگر آفتاب مستقیم شدید دارد، طی چند روز به‌تدریج عادتش دهید. آبیاری را کم و عمیق انجام دهید و اجازه دهید خاک کاملاً خشک شود. برگ‌ها و بخش‌های خشک‌شده را با دستکش جدا کنید. ساقه‌ها را از نظر نرمی، سیاه‌شدگی یا شپشک سفید بررسی کنید و هرگز نگذارید آب در زیرگلدانی بماند.	openai	{"is_plant":true,"persian_name":"افوربیا تریگونا یا درخت شیر آفریقایی","scientific_name":"Euphorbia trigona","confidence":94,"difficulty_level":"easy","light_requirement":"نور زیاد و غیرمستقیم؛ کنار پنجره پرنور شرقی یا جنوبی با آفتاب ملایم چند ساعت در روز مناسب است. در گوشه کم‌نور رشدش باریک و برگ‌ها خشک می‌شوند.","watering_schedule":"فقط وقتی خاک تا عمق زیاد کاملاً خشک شد آبیاری کنید؛ معمولاً بهار و تابستان هر ۲ تا ۳ هفته و پاییز و زمستان هر ۴ تا ۶ هفته. بعد از آبیاری، آب زیرگلدانی را خالی کنید.","humidity":"رطوبت معمول خانه کافی است؛ به غبارپاشی نیاز ندارد و رطوبت زیاد می‌تواند باعث پوسیدگی ساقه شود.","temperature":"دمای مناسب ۱۸ تا ۳۰ درجه سانتی‌گراد است. از سرما، باد کولر و دمای زیر ۱۲ درجه دور نگه دارید.","soil_mix":"خاک بسیار سبک و زهکش‌دار؛ ترکیب مناسب: خاک کاکتوس به‌همراه پرلیت یا پومیس و کمی ماسه درشت. خاک سنگین و همیشه مرطوب برای این گیاه خطرناک است.","fertilizer_recommendation":"در بهار و تابستان ماهی یک‌بار کود مخصوص کاکتوس و ساکولنت با نصف غلظت استفاده شود. در پاییز و زمستان کوددهی را قطع کنید.","potting_advice":"گلدان حتماً سوراخ زهکشی داشته باشد و به‌دلیل قد بلند گیاه، گلدان نسبتاً سنگین و پایدار انتخاب شود. سنگ‌ریزه روی خاک اشکالی ندارد، اما نباید مانع خشک شدن خاک شود.","repotting_interval":"هر ۲ تا ۳ سال یک‌بار یا زمانی که ریشه‌ها گلدان را پر کردند؛ بهترین زمان تعویض گلدان اوایل بهار است.","propagation_methods":["قلمه ساقه پس از خشک شدن محل برش به مدت ۳ تا ۷ روز","قلمه شاخه‌های جانبی و کاشت در خاک خشک و سبک"],"common_pests":["شپشک آردآلود","کنه تارعنکبوتی"],"common_diseases":["پوسیدگی ریشه بر اثر آبیاری زیاد","پوسیدگی و لکه‌های نرم ساقه در رطوبت یا سرمای زیاد"],"toxicity_pets":"برای گربه و سگ سمی است؛ شیره سفید آن می‌تواند باعث تحریک دهان، استفراغ، سوزش پوست و چشم شود.","toxicity_humans":"شیره سفید گیاه برای پوست و چشم محرک و سوزاننده است؛ هنگام قلمه‌گیری یا جابه‌جایی از دستکش استفاده کنید و آن را دور از دسترس کودکان نگه دارید.","preventive_care_tips":"گیاه را به محل پرنورتر منتقل کنید، اما اگر آفتاب مستقیم شدید دارد، طی چند روز به‌تدریج عادتش دهید. آبیاری را کم و عمیق انجام دهید و اجازه دهید خاک کاملاً خشک شود. برگ‌ها و بخش‌های خشک‌شده را با دستکش جدا کنید. ساقه‌ها را از نظر نرمی، سیاه‌شدگی یا شپشک سفید بررسی کنید و هرگز نگذارید آب در زیرگلدانی بماند."}	f	2026-08-14 19:28:36.478013+00	2026-08-14 19:28:36.478013+00	pending	\N	\N
2	1	AgACAgQAAxkBAANPan_3LIVJXsiOqey2CgS8ONEIlm0AAmEPaxv0_gFQ9lcIoDO9cL0BAAMCAAN5AAM9BA	دراسنا مارگیناتا یا درخت اژدها	Dracaena marginata	92	easy	نور زیاد و غیرمستقیم بهترین حالت است؛ کنار پنجره روشن با پرده یا فاصله از شیشه مناسب است. نور کم را تحمل می‌کند ولی رشد کم و برگ‌ها کم‌رنگ می‌شوند. آفتاب مستقیم تند می‌تواند نوک برگ‌ها را بسوزاند.	هر وقت ۳ تا ۵ سانتی‌متر بالای خاک خشک شد آبیاری کنید. معمولاً در فضای اداری هر ۷ تا ۱۴ روز یک‌بار کافی است، ولی در زمستان کمتر. آب اضافی زیرگلدانی حتماً تخلیه شود.	رطوبت معمولی خانه و اداره برای آن قابل‌قبول است. اگر نوک برگ‌ها خشک و قهوه‌ای شد، هفته‌ای چند بار غبارپاشی سبک یا گذاشتن ظرف آب کنار گیاه کمک می‌کند.	دمای مناسب ۱۸ تا ۲۷ درجه سانتی‌گراد است. از باد سرد کولر، بخاری مستقیم و دمای زیر ۱۲ درجه دور نگه داشته شود.	خاک سبک و با زهکشی خوب مناسب است؛ ترکیب پیشنهادی: ۲ قسمت خاک گلدانی، ۱ قسمت پرلیت یا پوکه ریز، ۱ قسمت کوکوپیت یا پیت‌ماس. خاک سنگین و همیشه خیس باعث پوسیدگی ریشه می‌شود.	در بهار و تابستان ماهی یک‌بار کود کامل گیاهان آپارتمانی با نصف دوز توصیه‌شده بدهید. در پاییز و زمستان کوددهی را قطع یا خیلی کم کنید. کود زیاد باعث سوختگی نوک برگ‌ها می‌شود.	گلدان باید سوراخ زهکش داشته باشد. چون ساقه‌ها بلند و باریک هستند، گلدان نسبتاً سنگین و پایدار انتخاب کنید تا گیاه واژگون نشود. سطح خاک بهتر است خیلی فشرده نباشد.	هر ۲ تا ۳ سال یک‌بار یا وقتی ریشه‌ها از زهکش بیرون زدند تعویض گلدان انجام شود. فقط یک سایز بزرگ‌تر انتخاب کنید تا خاک اضافی خیس نماند.	قلمه ساقه در آب یا خاک سبک\nقلمه سرشاخه و ریشه‌دار کردن در محیط گرم و روشن	شپشک آردآلود\nکنه تارعنکبوتی	پوسیدگی ریشه بر اثر آبیاری زیاد\nلکه برگی در اثر رطوبت زیاد و تهویه ضعیف	برای سگ و گربه سمی است و در صورت جویدن می‌تواند باعث استفراغ، بی‌حالی، آب‌ریزش دهان و بی‌اشتهایی شود؛ دور از دسترس حیوانات نگه دارید.	برای انسان معمولاً خطر جدی ندارد، اما خوردن برگ‌ها می‌تواند باعث تحریک دهان و معده شود؛ دور از دسترس کودکان کوچک باشد.	مهم‌ترین نکته برای این دراسنا آبیاری کنترل‌شده است؛ قبل از آبیاری خشکی سطح خاک را بررسی کنید. برگ‌های خشک و قهوه‌ای را با قیچی تمیز حذف کنید. هر چند هفته یک‌بار برگ‌ها را با دستمال مرطوب تمیز کنید تا بهتر فتوسنتز کند. گیاه را نزدیک جریان مستقیم کولر یا بخاری نگذارید و برای رشد یکنواخت، هر ماه گلدان را کمی بچرخانید.	openai	{"is_plant":true,"persian_name":"دراسنا مارگیناتا یا درخت اژدها","scientific_name":"Dracaena marginata","confidence":92,"difficulty_level":"easy","light_requirement":"نور زیاد و غیرمستقیم بهترین حالت است؛ کنار پنجره روشن با پرده یا فاصله از شیشه مناسب است. نور کم را تحمل می‌کند ولی رشد کم و برگ‌ها کم‌رنگ می‌شوند. آفتاب مستقیم تند می‌تواند نوک برگ‌ها را بسوزاند.","watering_schedule":"هر وقت ۳ تا ۵ سانتی‌متر بالای خاک خشک شد آبیاری کنید. معمولاً در فضای اداری هر ۷ تا ۱۴ روز یک‌بار کافی است، ولی در زمستان کمتر. آب اضافی زیرگلدانی حتماً تخلیه شود.","humidity":"رطوبت معمولی خانه و اداره برای آن قابل‌قبول است. اگر نوک برگ‌ها خشک و قهوه‌ای شد، هفته‌ای چند بار غبارپاشی سبک یا گذاشتن ظرف آب کنار گیاه کمک می‌کند.","temperature":"دمای مناسب ۱۸ تا ۲۷ درجه سانتی‌گراد است. از باد سرد کولر، بخاری مستقیم و دمای زیر ۱۲ درجه دور نگه داشته شود.","soil_mix":"خاک سبک و با زهکشی خوب مناسب است؛ ترکیب پیشنهادی: ۲ قسمت خاک گلدانی، ۱ قسمت پرلیت یا پوکه ریز، ۱ قسمت کوکوپیت یا پیت‌ماس. خاک سنگین و همیشه خیس باعث پوسیدگی ریشه می‌شود.","fertilizer_recommendation":"در بهار و تابستان ماهی یک‌بار کود کامل گیاهان آپارتمانی با نصف دوز توصیه‌شده بدهید. در پاییز و زمستان کوددهی را قطع یا خیلی کم کنید. کود زیاد باعث سوختگی نوک برگ‌ها می‌شود.","potting_advice":"گلدان باید سوراخ زهکش داشته باشد. چون ساقه‌ها بلند و باریک هستند، گلدان نسبتاً سنگین و پایدار انتخاب کنید تا گیاه واژگون نشود. سطح خاک بهتر است خیلی فشرده نباشد.","repotting_interval":"هر ۲ تا ۳ سال یک‌بار یا وقتی ریشه‌ها از زهکش بیرون زدند تعویض گلدان انجام شود. فقط یک سایز بزرگ‌تر انتخاب کنید تا خاک اضافی خیس نماند.","propagation_methods":["قلمه ساقه در آب یا خاک سبک","قلمه سرشاخه و ریشه‌دار کردن در محیط گرم و روشن"],"common_pests":["شپشک آردآلود","کنه تارعنکبوتی"],"common_diseases":["پوسیدگی ریشه بر اثر آبیاری زیاد","لکه برگی در اثر رطوبت زیاد و تهویه ضعیف"],"toxicity_pets":"برای سگ و گربه سمی است و در صورت جویدن می‌تواند باعث استفراغ، بی‌حالی، آب‌ریزش دهان و بی‌اشتهایی شود؛ دور از دسترس حیوانات نگه دارید.","toxicity_humans":"برای انسان معمولاً خطر جدی ندارد، اما خوردن برگ‌ها می‌تواند باعث تحریک دهان و معده شود؛ دور از دسترس کودکان کوچک باشد.","preventive_care_tips":"مهم‌ترین نکته برای این دراسنا آبیاری کنترل‌شده است؛ قبل از آبیاری خشکی سطح خاک را بررسی کنید. برگ‌های خشک و قهوه‌ای را با قیچی تمیز حذف کنید. هر چند هفته یک‌بار برگ‌ها را با دستمال مرطوب تمیز کنید تا بهتر فتوسنتز کند. گیاه را نزدیک جریان مستقیم کولر یا بخاری نگذارید و برای رشد یکنواخت، هر ماه گلدان را کمی بچرخانید."}	f	2026-08-15 05:21:50.101411+00	2026-08-15 05:21:50.101411+00	pending	\N	\N
3	1	AgACAgQAAxkBAANNan_2KzI29Hr7uqgqN7eSxsD0pmUAAmAPaxv0_gFQxC5tsMZ-lVUBAAMCAAN5AAM9BA	نامشخص	\N	0	unknown	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.	openai		f	2026-08-15 05:16:25.173672+00	2026-08-15 05:16:25.173672+00	pending	\N	\N
4	1	AgACAgQAAxkBAAN2aoB3TZuUdL4GTrfYvazvvkZ_6EEAAs8Paxv0_gFQI6SLW7eg7K0BAAMCAAN5AAM9BA	زامیفولیا یا گیاه زی‌زی	Zamioculcas zamiifolia	89	easy	نور زیادِ غیرمستقیم بهترین حالت است؛ نور کم را تحمل می‌کند اما رشد کند می‌شود. آفتاب مستقیم کنار پنجره، مخصوصاً ظهر، می‌تواند باعث زردی و لکه‌سوختگی برگ‌ها شود.	فقط وقتی ۵ تا ۷ سانتی‌متر بالای خاک کاملاً خشک شد آبیاری کنید. معمولاً در خانه هر ۲ تا ۳ هفته یک‌بار کافی است و در زمستان کمتر. آب اضافی زیرگلدانی را حتماً خالی کنید.	رطوبت معمولی خانه برای زامیفولیا کافی است. غبارپاشی لازم نیست و اگر برگ‌ها لکه‌دار هستند بهتر است برگ‌ها خیس نمانند.	دمای مناسب ۱۸ تا ۲۸ درجه سانتی‌گراد است. از سرمای زیر ۱۲ درجه، باد کولر، بخاری مستقیم و تغییر دمای ناگهانی دور نگه دارید.	خاک سبک و بسیار زهکش‌دار مناسب است؛ ترکیب پیشنهادی: خاک گلدانی باکیفیت + پرلیت یا پومیس + کمی کوکوپیت. خاک سنگین و همیشه خیس باعث پوسیدگی ریزوم‌ها می‌شود.	در بهار و تابستان ماهی یک‌بار کود کامل رقیق‌شده با نصف دوز مصرف کنید. در پاییز و زمستان کود ندهید. اگر گیاه زرد و لکه‌دار است ابتدا آبیاری و زهکش را اصلاح کنید، سپس کوددهی انجام دهید.	گلدان باید حتماً سوراخ زهکش داشته باشد و خیلی بزرگ‌تر از حجم ریشه نباشد. زامیفولیا ریزوم‌های گوشتی دارد و در گلدان بیش از حد بزرگ، خاک دیر خشک می‌شود و احتمال پوسیدگی بالا می‌رود.	هر ۲ تا ۳ سال یک‌بار یا وقتی ریزوم‌ها گلدان را پر کردند و رشد متوقف شد. بهترین زمان تعویض گلدان بهار است.	تقسیم ریزوم و جدا کردن بوته‌های کناری هنگام تعویض گلدان\nقلمه برگ یا برگچه در خاک سبک؛ این روش کند است و ممکن است چند ماه طول بکشد	شپشک آردآلود\nکنه تارعنکبوتی	پوسیدگی ریشه و ریزوم بر اثر آبیاری زیاد\nلکه برگی قارچی یا باکتریایی در اثر رطوبت زیاد و خیس ماندن برگ‌ها	برای گربه و سگ سمی محسوب می‌شود و جویدن برگ‌ها می‌تواند باعث سوزش دهان، آبریزش، تهوع یا ناراحتی گوارشی شود؛ دور از دسترس حیوانات نگه دارید.	برای انسان خوراکی نیست و شیره گیاه می‌تواند باعث تحریک پوست و دهان شود. هنگام هرس یا تقسیم بوته بهتر است دستکش استفاده شود.	برگ‌های زرد و لکه‌دار را با قیچی تمیز جدا کنید و گیاه را کمی دورتر از آفتاب مستقیم قرار دهید. قبل از هر آبیاری خشکی خاک را با انگشت بررسی کنید، برگ‌ها را خیس نکنید، جریان هوای ملایم فراهم کنید و ماهی یک‌بار پشت و روی برگ‌ها را برای شپشک و کنه بررسی کنید.	openai	{"is_plant":true,"persian_name":"زامیفولیا یا گیاه زی‌زی","scientific_name":"Zamioculcas zamiifolia","confidence":89,"difficulty_level":"easy","light_requirement":"نور زیادِ غیرمستقیم بهترین حالت است؛ نور کم را تحمل می‌کند اما رشد کند می‌شود. آفتاب مستقیم کنار پنجره، مخصوصاً ظهر، می‌تواند باعث زردی و لکه‌سوختگی برگ‌ها شود.","watering_schedule":"فقط وقتی ۵ تا ۷ سانتی‌متر بالای خاک کاملاً خشک شد آبیاری کنید. معمولاً در خانه هر ۲ تا ۳ هفته یک‌بار کافی است و در زمستان کمتر. آب اضافی زیرگلدانی را حتماً خالی کنید.","humidity":"رطوبت معمولی خانه برای زامیفولیا کافی است. غبارپاشی لازم نیست و اگر برگ‌ها لکه‌دار هستند بهتر است برگ‌ها خیس نمانند.","temperature":"دمای مناسب ۱۸ تا ۲۸ درجه سانتی‌گراد است. از سرمای زیر ۱۲ درجه، باد کولر، بخاری مستقیم و تغییر دمای ناگهانی دور نگه دارید.","soil_mix":"خاک سبک و بسیار زهکش‌دار مناسب است؛ ترکیب پیشنهادی: خاک گلدانی باکیفیت + پرلیت یا پومیس + کمی کوکوپیت. خاک سنگین و همیشه خیس باعث پوسیدگی ریزوم‌ها می‌شود.","fertilizer_recommendation":"در بهار و تابستان ماهی یک‌بار کود کامل رقیق‌شده با نصف دوز مصرف کنید. در پاییز و زمستان کود ندهید. اگر گیاه زرد و لکه‌دار است ابتدا آبیاری و زهکش را اصلاح کنید، سپس کوددهی انجام دهید.","potting_advice":"گلدان باید حتماً سوراخ زهکش داشته باشد و خیلی بزرگ‌تر از حجم ریشه نباشد. زامیفولیا ریزوم‌های گوشتی دارد و در گلدان بیش از حد بزرگ، خاک دیر خشک می‌شود و احتمال پوسیدگی بالا می‌رود.","repotting_interval":"هر ۲ تا ۳ سال یک‌بار یا وقتی ریزوم‌ها گلدان را پر کردند و رشد متوقف شد. بهترین زمان تعویض گلدان بهار است.","propagation_methods":["تقسیم ریزوم و جدا کردن بوته‌های کناری هنگام تعویض گلدان","قلمه برگ یا برگچه در خاک سبک؛ این روش کند است و ممکن است چند ماه طول بکشد"],"common_pests":["شپشک آردآلود","کنه تارعنکبوتی"],"common_diseases":["پوسیدگی ریشه و ریزوم بر اثر آبیاری زیاد","لکه برگی قارچی یا باکتریایی در اثر رطوبت زیاد و خیس ماندن برگ‌ها"],"toxicity_pets":"برای گربه و سگ سمی محسوب می‌شود و جویدن برگ‌ها می‌تواند باعث سوزش دهان، آبریزش، تهوع یا ناراحتی گوارشی شود؛ دور از دسترس حیوانات نگه دارید.","toxicity_humans":"برای انسان خوراکی نیست و شیره گیاه می‌تواند باعث تحریک پوست و دهان شود. هنگام هرس یا تقسیم بوته بهتر است دستکش استفاده شود.","preventive_care_tips":"برگ‌های زرد و لکه‌دار را با قیچی تمیز جدا کنید و گیاه را کمی دورتر از آفتاب مستقیم قرار دهید. قبل از هر آبیاری خشکی خاک را با انگشت بررسی کنید، برگ‌ها را خیس نکنید، جریان هوای ملایم فراهم کنید و ماهی یک‌بار پشت و روی برگ‌ها را برای شپشک و کنه بررسی کنید."}	t	2026-08-15 14:27:22.863144+00	2026-08-15 15:27:58.836784+00	pending	\N	\N
5	1	AgACAgQAAxkBAAOfaoHtD5xTMf7iLHsjko2PobfVS54AAlQPaxu0gRFQavrIVO5pWfMBAAMCAAN4AAM9BA	نامشخص	\N	0	unknown	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.	openai		f	2026-08-16 18:22:32.621803+00	2026-08-16 18:22:32.621803+00	pending	\N	\N
6	1	AgACAgQAAxkBAAOfaoHtD5xTMf7iLHsjko2PobfVS54AAlQPaxu0gRFQavrIVO5pWfMBAAMCAAN4AAM9BA	نامشخص	\N	0	unknown	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	پاسخ قابل‌فهمی از هوش مصنوعی دریافت نشد.	openai		f	2026-08-18 15:46:53.274482+00	2026-08-18 15:46:53.274482+00	pending	\N	\N
\.


--
-- Data for Name: plants; Type: TABLE DATA; Schema: public; Owner: greenvita
--

COPY public.plants (id, owner_id, name, species, notes, health_status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reminders; Type: TABLE DATA; Schema: public; Owner: greenvita
--

COPY public.reminders (id, user_id, plant_id, reminder_type, interval_days, next_run_at, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: greenvita
--

COPY public.users (id, telegram_id, username, first_name, last_name, phone_number, language_code, is_admin, is_blocked, created_at, updated_at) FROM stdin;
1	65551599	Armin_Naghizadeh	Armin	Naghizadeh	\N	en	f	f	2026-08-14 16:45:04.369118+00	2026-08-14 16:45:04.369118+00
\.


--
-- Name: conversations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: greenvita
--

SELECT pg_catalog.setval('public.conversations_id_seq', 1, false);


--
-- Name: diagnoses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: greenvita
--

SELECT pg_catalog.setval('public.diagnoses_id_seq', 10, true);


--
-- Name: plant_identifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: greenvita
--

SELECT pg_catalog.setval('public.plant_identifications_id_seq', 6, true);


--
-- Name: plants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: greenvita
--

SELECT pg_catalog.setval('public.plants_id_seq', 1, true);


--
-- Name: reminders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: greenvita
--

SELECT pg_catalog.setval('public.reminders_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: greenvita
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: diagnoses diagnoses_pkey; Type: CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.diagnoses
    ADD CONSTRAINT diagnoses_pkey PRIMARY KEY (id);


--
-- Name: plant_identifications plant_identifications_pkey; Type: CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.plant_identifications
    ADD CONSTRAINT plant_identifications_pkey PRIMARY KEY (id);


--
-- Name: plants plants_pkey; Type: CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.plants
    ADD CONSTRAINT plants_pkey PRIMARY KEY (id);


--
-- Name: reminders reminders_pkey; Type: CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_conversations_plant_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_conversations_plant_id ON public.conversations USING btree (plant_id);


--
-- Name: ix_conversations_user_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_conversations_user_id ON public.conversations USING btree (user_id);


--
-- Name: ix_diagnoses_plant_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_diagnoses_plant_id ON public.diagnoses USING btree (plant_id);


--
-- Name: ix_diagnoses_user_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_diagnoses_user_id ON public.diagnoses USING btree (user_id);


--
-- Name: ix_plant_identifications_user_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_plant_identifications_user_id ON public.plant_identifications USING btree (user_id);


--
-- Name: ix_plants_owner_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_plants_owner_id ON public.plants USING btree (owner_id);


--
-- Name: ix_reminders_plant_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_reminders_plant_id ON public.reminders USING btree (plant_id);


--
-- Name: ix_reminders_user_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE INDEX ix_reminders_user_id ON public.reminders USING btree (user_id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: greenvita
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: conversations conversations_plant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_plant_id_fkey FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE SET NULL;


--
-- Name: conversations conversations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: diagnoses diagnoses_plant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.diagnoses
    ADD CONSTRAINT diagnoses_plant_id_fkey FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE SET NULL;


--
-- Name: diagnoses diagnoses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.diagnoses
    ADD CONSTRAINT diagnoses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: plant_identifications plant_identifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.plant_identifications
    ADD CONSTRAINT plant_identifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: plants plants_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.plants
    ADD CONSTRAINT plants_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: reminders reminders_plant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_plant_id_fkey FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE CASCADE;


--
-- Name: reminders reminders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: greenvita
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict r9XKGM3P5cIdXbAOGb86cP77gDruMBofGwrae22cs0dxw2T6WX80h0qfPE4WC87

