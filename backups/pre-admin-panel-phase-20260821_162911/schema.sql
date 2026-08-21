--
-- PostgreSQL database dump
--

\restrict HJfHSlJSSvcx07XHuPYlCYvV80NJF9WxGgMBAi8SlU46np3EawgpHrtEYbznWd2

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
-- Name: diagnosisseverity; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.diagnosisseverity AS ENUM (
    'none',
    'mild',
    'moderate',
    'severe',
    'unknown'
);


--
-- Name: difficultylevel; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.difficultylevel AS ENUM (
    'easy',
    'medium',
    'hard',
    'unknown'
);


--
-- Name: messagerole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.messagerole AS ENUM (
    'user',
    'assistant',
    'system'
);


--
-- Name: planthealthstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.planthealthstatus AS ENUM (
    'healthy',
    'sick',
    'under_treatment',
    'recovered',
    'unknown'
);


--
-- Name: remindertype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.remindertype AS ENUM (
    'watering',
    'fertilizing',
    'other'
);


--
-- Name: visitstatus; Type: TYPE; Schema: public; Owner: -
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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conversations_id_seq OWNED BY public.conversations.id;


--
-- Name: diagnoses; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: diagnoses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.diagnoses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: diagnoses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.diagnoses_id_seq OWNED BY public.diagnoses.id;


--
-- Name: plant_identifications; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: plant_identifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plant_identifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plant_identifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plant_identifications_id_seq OWNED BY public.plant_identifications.id;


--
-- Name: plants; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: plants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plants_id_seq OWNED BY public.plants.id;


--
-- Name: reminders; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: reminders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reminders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reminders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reminders_id_seq OWNED BY public.reminders.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: conversations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations ALTER COLUMN id SET DEFAULT nextval('public.conversations_id_seq'::regclass);


--
-- Name: diagnoses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diagnoses ALTER COLUMN id SET DEFAULT nextval('public.diagnoses_id_seq'::regclass);


--
-- Name: plant_identifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plant_identifications ALTER COLUMN id SET DEFAULT nextval('public.plant_identifications_id_seq'::regclass);


--
-- Name: plants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plants ALTER COLUMN id SET DEFAULT nextval('public.plants_id_seq'::regclass);


--
-- Name: reminders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reminders ALTER COLUMN id SET DEFAULT nextval('public.reminders_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: diagnoses diagnoses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diagnoses
    ADD CONSTRAINT diagnoses_pkey PRIMARY KEY (id);


--
-- Name: plant_identifications plant_identifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plant_identifications
    ADD CONSTRAINT plant_identifications_pkey PRIMARY KEY (id);


--
-- Name: plants plants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plants
    ADD CONSTRAINT plants_pkey PRIMARY KEY (id);


--
-- Name: reminders reminders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_conversations_plant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversations_plant_id ON public.conversations USING btree (plant_id);


--
-- Name: ix_conversations_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversations_user_id ON public.conversations USING btree (user_id);


--
-- Name: ix_diagnoses_plant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_diagnoses_plant_id ON public.diagnoses USING btree (plant_id);


--
-- Name: ix_diagnoses_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_diagnoses_user_id ON public.diagnoses USING btree (user_id);


--
-- Name: ix_plant_identifications_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_plant_identifications_user_id ON public.plant_identifications USING btree (user_id);


--
-- Name: ix_plants_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_plants_owner_id ON public.plants USING btree (owner_id);


--
-- Name: ix_reminders_plant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reminders_plant_id ON public.reminders USING btree (plant_id);


--
-- Name: ix_reminders_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_reminders_user_id ON public.reminders USING btree (user_id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: conversations conversations_plant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_plant_id_fkey FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE SET NULL;


--
-- Name: conversations conversations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: diagnoses diagnoses_plant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diagnoses
    ADD CONSTRAINT diagnoses_plant_id_fkey FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE SET NULL;


--
-- Name: diagnoses diagnoses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diagnoses
    ADD CONSTRAINT diagnoses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: plant_identifications plant_identifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plant_identifications
    ADD CONSTRAINT plant_identifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: plants plants_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plants
    ADD CONSTRAINT plants_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: reminders reminders_plant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_plant_id_fkey FOREIGN KEY (plant_id) REFERENCES public.plants(id) ON DELETE CASCADE;


--
-- Name: reminders reminders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict HJfHSlJSSvcx07XHuPYlCYvV80NJF9WxGgMBAi8SlU46np3EawgpHrtEYbznWd2

