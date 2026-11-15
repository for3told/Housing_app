--
-- PostgreSQL database dump
--

\restrict hSvRnw3E95ndCT28OBqjJwUm36z6l3szjfC8Ob7Uqqefvdpkz18e9dNyYU1pI39

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: update_apartment_resident_count(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_apartment_resident_count() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE apartments SET resident_count = resident_count + 1 WHERE id = NEW.apartment_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE apartments SET resident_count = resident_count - 1 WHERE id = OLD.apartment_id;
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        IF (OLD.apartment_id IS DISTINCT FROM NEW.apartment_id) THEN
            IF OLD.apartment_id IS NOT NULL THEN
                UPDATE apartments SET resident_count = resident_count - 1 WHERE id = OLD.apartment_id;
            END IF;
            IF NEW.apartment_id IS NOT NULL THEN
                UPDATE apartments SET resident_count = resident_count + 1 WHERE id = NEW.apartment_id;
            END IF;
        END IF;
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.update_apartment_resident_count() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: apartments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.apartments (
    id integer NOT NULL,
    building_id integer,
    entrance integer NOT NULL,
    floor integer NOT NULL,
    apartment_number character varying(20) NOT NULL,
    resident_count integer DEFAULT 0
);


ALTER TABLE public.apartments OWNER TO postgres;

--
-- Name: apartments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.apartments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.apartments_id_seq OWNER TO postgres;

--
-- Name: apartments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.apartments_id_seq OWNED BY public.apartments.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    user_id integer,
    user_name_snapshot character varying(150) NOT NULL,
    action_type character varying(50) NOT NULL,
    description text,
    ip_address character varying(50),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO postgres;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: buildings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.buildings (
    id integer NOT NULL,
    address character varying(255) NOT NULL,
    floors_count integer NOT NULL,
    entrances_count integer NOT NULL,
    apartments_count integer NOT NULL,
    total_residents integer DEFAULT 0
);


ALTER TABLE public.buildings OWNER TO postgres;

--
-- Name: buildings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.buildings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.buildings_id_seq OWNER TO postgres;

--
-- Name: buildings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.buildings_id_seq OWNED BY public.buildings.id;


--
-- Name: poll_options; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.poll_options (
    id integer NOT NULL,
    poll_id integer,
    option_text character varying(255) NOT NULL
);


ALTER TABLE public.poll_options OWNER TO postgres;

--
-- Name: poll_options_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.poll_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poll_options_id_seq OWNER TO postgres;

--
-- Name: poll_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.poll_options_id_seq OWNED BY public.poll_options.id;


--
-- Name: polls; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.polls (
    id integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    building_id integer,
    created_by integer,
    expires_at timestamp without time zone NOT NULL,
    is_anonymous boolean DEFAULT false,
    is_active boolean DEFAULT true,
    is_closed boolean DEFAULT false
);


ALTER TABLE public.polls OWNER TO postgres;

--
-- Name: polls_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.polls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.polls_id_seq OWNER TO postgres;

--
-- Name: polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.polls_id_seq OWNED BY public.polls.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    role_name character varying(50) NOT NULL,
    description text
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    last_name character varying(50) NOT NULL,
    first_name character varying(50) NOT NULL,
    middle_name character varying(50),
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    apartment_id integer,
    role_id integer NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.votes (
    id integer NOT NULL,
    poll_id integer,
    user_id integer,
    option_id integer,
    voted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.votes OWNER TO postgres;

--
-- Name: votes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.votes_id_seq OWNER TO postgres;

--
-- Name: votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.votes_id_seq OWNED BY public.votes.id;


--
-- Name: apartments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.apartments ALTER COLUMN id SET DEFAULT nextval('public.apartments_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: buildings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.buildings ALTER COLUMN id SET DEFAULT nextval('public.buildings_id_seq'::regclass);


--
-- Name: poll_options id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_options ALTER COLUMN id SET DEFAULT nextval('public.poll_options_id_seq'::regclass);


--
-- Name: polls id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.polls ALTER COLUMN id SET DEFAULT nextval('public.polls_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: votes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes ALTER COLUMN id SET DEFAULT nextval('public.votes_id_seq'::regclass);


--
-- Data for Name: apartments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.apartments (id, building_id, entrance, floor, apartment_number, resident_count) FROM stdin;
2	1	1	1	2	0
3	1	1	1	3	0
4	1	1	1	4	0
5	1	1	2	5	0
6	1	1	2	6	0
7	1	1	2	7	0
8	1	1	2	8	0
9	1	1	3	9	0
10	1	1	3	10	0
11	1	1	3	11	0
12	1	1	3	12	0
13	1	1	4	13	0
14	1	1	4	14	0
15	1	1	4	15	0
16	1	1	4	16	0
17	1	1	5	17	0
18	1	1	5	18	0
19	1	1	5	19	0
20	1	1	5	20	0
21	1	1	5	21	0
22	1	2	1	22	0
23	1	2	1	23	0
24	1	2	1	24	0
25	1	2	1	25	0
26	1	2	2	26	0
27	1	2	2	27	0
28	1	2	2	28	0
29	1	2	2	29	0
30	1	2	3	30	0
31	1	2	3	31	0
32	1	2	3	32	0
33	1	2	3	33	0
34	1	2	4	34	0
35	1	2	4	35	0
36	1	2	4	36	0
37	1	2	4	37	0
38	1	2	5	38	0
39	1	2	5	39	0
40	1	2	5	40	0
43	2	1	1	2	0
44	2	1	1	3	0
45	2	1	1	4	0
46	2	1	2	5	0
47	2	1	2	6	0
49	2	1	2	8	0
50	2	1	3	9	0
51	2	1	3	10	0
52	2	1	3	11	0
53	2	1	3	12	0
54	2	1	4	13	0
55	2	1	4	14	0
56	2	1	4	15	0
57	2	1	4	16	0
58	2	1	5	17	0
59	2	1	5	18	0
60	2	1	5	19	0
61	2	1	5	20	0
62	2	1	5	21	0
63	2	1	5	22	0
64	2	1	5	23	0
65	2	1	5	24	0
48	2	1	2	7	1
42	2	1	1	1	1
1	1	1	1	1	1
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_logs (id, user_id, user_name_snapshot, action_type, description, ip_address, created_at) FROM stdin;
1	1	Гражданинов Гражданин	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 14:22:46.692801
2	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:24:40.437468
3	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:32:22.181346
4	2	Пользователев Пользователь	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 14:34:09.837007
5	2	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:34:13.33451
6	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:34:19.656174
7	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:35:59.080605
8	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:37:54.422733
9	2	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:00:02.743944
10	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:00:11.209213
11	1	Гражданинов Гражданин	ADD_BUILDING	Дом по адресу 'ул. 17 Героев, д.1' добавлен, сгенерировано квартир: 40	127.0.0.1	2026-11-15 15:00:50.618919
12	2	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:08:53.455505
13	2	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:09:15.325395
14	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:14:54.477425
15	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:18:26.919252
16	1	Гражданинов Гражданин	ADD_BUILDING	Дом по адресу 'ул. Ершова, д.10' добавлен, квартир: 24	127.0.0.1	2026-11-15 15:19:19.853791
17	1	Гражданинов Гражданин	EDIT_BUILDING	Обновлены данные дома ID 2	127.0.0.1	2026-11-15 15:19:55.914064
18	3	Простаков Простак	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 15:21:11.109318
19	3	Простаков Простак	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:21:16.019384
20	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:21:32.334923
21	2	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:29:03.497284
22	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:29:39.217275
23	1	Гражданинов Гражданин	ADD_BUILDING	Добавлен дом 'ул. Садовая, д. 11' (генерация квартир: False)	127.0.0.1	2026-11-15 15:33:36.188162
24	4	Яшагин Лев	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 15:41:40.012576
25	4	Яшагин Лев	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:41:44.151922
26	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:42:05.868777
27	1	Гражданинов Гражданин	EDIT_BUILDING	Обновлены данные дома ID 3	127.0.0.1	2026-11-15 15:42:17.520079
28	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:52:32.994661
29	1	Гражданинов Гражданин	CREATE_POLL	Создано голосование ID 1	127.0.0.1	2026-11-15 15:53:31.291016
30	1	Гражданинов Гражданин	VOTE	Участие в голосовании ID 1	127.0.0.1	2026-11-15 15:53:38.361473
31	4	Яшагин Лев	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:53:47.089207
32	4	Яшагин Лев	VOTE	Участие в голосовании ID 1	127.0.0.1	2026-11-15 15:53:51.973206
33	3	Простаков Простак	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:53:56.54322
34	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:05.649943
35	1	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:13.882002
36	2	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:20.109432
37	3	Простаков Простак	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:27.108358
38	5	Печкин Георгий	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 15:56:30.975465
39	5	Печкин Георгий	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:56:33.859172
\.


--
-- Data for Name: buildings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.buildings (id, address, floors_count, entrances_count, apartments_count, total_residents) FROM stdin;
1	ул. 17 Героев, д.1	5	2	40	0
2	ул. Ершова, д.10	6	1	24	0
3	ул. Садовая, д. 11	1	1	0	0
\.


--
-- Data for Name: poll_options; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.poll_options (id, poll_id, option_text) FROM stdin;
1	1	Да
2	1	Нет
\.


--
-- Data for Name: polls; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.polls (id, title, description, building_id, created_by, expires_at, is_anonymous, is_active, is_closed) FROM stdin;
1	Установка шлагбаума на въезде в ЖК		2	1	2026-11-20 15:00:00	t	t	f
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, role_name, description) FROM stdin;
1	admin	Администратор системы
2	dispatcher	Диспетчер УК
3	resident	Жилец многоквартирного дома
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, last_name, first_name, middle_name, username, password_hash, apartment_id, role_id) FROM stdin;
1	Гражданинов	Гражданин	Гражданович	neOper	scrypt:32768:8:1$Da7mkIUsyciqfekU$ef9eb7dfd25ed9f110aa39d128eac83bdaa92580138dd88c49aa8619527391080990a5d8b0ca3db1adc8387ad89c7439020d3fc99b5ca9b650baa5e50c020df7	1	1
2	Пользователев	Пользователь	Пользователевич	UserOK	scrypt:32768:8:1$DMe9J8l1Bv2Qq6J0$4b51ea30ed220dde4fa8fb99f190a1553fd69baecd48ba3c951cae7b7e4a845e28d9a4a316fc3544d8c446a1e623ea8ea61196f10c2a6b88ee76327477968c10	4	2
3	Простаков	Простак	Простакович	ProstOI	scrypt:32768:8:1$6l9GyjuqpRdf36Cv$4c74dcd68627b9c4d01b63378fbb10e07416b5d913555807b61caa3a0110bc804a445c1413da9d988d3ee15e929ac0b84c4af5d3a4cfd7694e80a5a0449cced0	48	3
4	Яшагин	Лев	Трофимович	lev.yashagin	scrypt:32768:8:1$myO9JHnVlohGRCEX$eeefcf66459380e2238558aa624fefd2143b71484ad44cec2f51ff03b722a4e808d304d9e7398f7c163aa084b35d48730dae2126e38d8d22237780f33fb93479	42	3
5	Печкин	Георгий	Ираклиевич	georgiy02031979	scrypt:32768:8:1$DMY7kodrtI34OchQ$64d9488bb87ddb7ab5f1d7792fa7a3ac50b1c8f88d59111fe56162c5ceea0c1d171f17da7b84804ea1cc75bb1af890ecd6464462ea28f17dcd949ca0e6792886	1	3
\.


--
-- Data for Name: votes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.votes (id, poll_id, user_id, option_id, voted_at) FROM stdin;
1	1	1	1	2026-11-15 15:53:38.350702
2	1	4	1	2026-11-15 15:53:51.966608
\.


--
-- Name: apartments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.apartments_id_seq', 66, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 39, true);


--
-- Name: buildings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.buildings_id_seq', 3, true);


--
-- Name: poll_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.poll_options_id_seq', 2, true);


--
-- Name: polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.polls_id_seq', 1, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_id_seq', 3, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 5, true);


--
-- Name: votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.votes_id_seq', 2, true);


--
-- Name: apartments apartments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.apartments
    ADD CONSTRAINT apartments_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: buildings buildings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.buildings
    ADD CONSTRAINT buildings_pkey PRIMARY KEY (id);


--
-- Name: poll_options poll_options_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_options
    ADD CONSTRAINT poll_options_pkey PRIMARY KEY (id);


--
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: roles roles_role_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_role_name_key UNIQUE (role_name);


--
-- Name: votes unique_user_poll; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT unique_user_poll UNIQUE (poll_id, user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: votes votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT votes_pkey PRIMARY KEY (id);


--
-- Name: users trg_update_resident_count; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_update_resident_count AFTER INSERT OR DELETE OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_apartment_resident_count();


--
-- Name: apartments apartments_building_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.apartments
    ADD CONSTRAINT apartments_building_id_fkey FOREIGN KEY (building_id) REFERENCES public.buildings(id) ON DELETE CASCADE;


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: poll_options poll_options_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_options
    ADD CONSTRAINT poll_options_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- Name: polls polls_building_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_building_id_fkey FOREIGN KEY (building_id) REFERENCES public.buildings(id) ON DELETE CASCADE;


--
-- Name: polls polls_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: votes votes_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT votes_option_id_fkey FOREIGN KEY (option_id) REFERENCES public.poll_options(id) ON DELETE CASCADE;


--
-- Name: votes votes_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT votes_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(id) ON DELETE CASCADE;


--
-- Name: votes votes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.votes
    ADD CONSTRAINT votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict hSvRnw3E95ndCT28OBqjJwUm36z6l3szjfC8Ob7Uqqefvdpkz18e9dNyYU1pI39

