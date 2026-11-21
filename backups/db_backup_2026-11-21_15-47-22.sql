--
-- PostgreSQL database dump
--

\restrict Lvu2pmceZeAHEuVZ01RomaRhvYV1ZPs5VvVUo1j5T81Ak4dYHOekKrj39NZoi3l

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
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.messages (
    id integer NOT NULL,
    sender_id integer NOT NULL,
    building_id integer,
    recipient_id integer,
    content text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_edited boolean DEFAULT false,
    CONSTRAINT chk_message_target CHECK ((((building_id IS NOT NULL) AND (recipient_id IS NULL)) OR ((building_id IS NULL) AND (recipient_id IS NOT NULL))))
);


ALTER TABLE public.messages OWNER TO postgres;

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.messages_id_seq OWNER TO postgres;

--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


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
    role_id integer NOT NULL,
    is_owner_requested boolean DEFAULT false,
    is_owner_verified boolean DEFAULT false
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
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


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
142	5	1	1	4	0
42	2	1	1	1	1
48	2	1	2	7	0
43	2	1	1	2	1
67	4	1	1	1	0
68	4	1	1	2	0
69	4	1	1	3	0
70	4	1	1	4	0
71	4	1	2	5	0
72	4	1	2	6	0
73	4	1	2	7	0
74	4	1	2	8	0
75	4	1	3	9	0
76	4	1	3	10	0
77	4	1	3	11	0
78	4	1	3	12	0
79	4	1	4	13	0
80	4	1	4	14	0
81	4	1	4	15	0
82	4	1	4	16	0
83	4	1	5	17	0
84	4	1	5	18	0
85	4	1	5	19	0
86	4	1	5	20	0
87	4	1	6	21	0
88	4	1	6	22	0
89	4	1	6	23	0
90	4	1	6	24	0
91	4	1	7	25	0
92	4	1	7	26	0
93	4	1	7	27	0
94	4	1	7	28	0
95	4	1	8	29	0
96	4	1	8	30	0
97	4	1	8	31	0
98	4	1	8	32	0
99	4	1	9	33	0
100	4	1	9	34	0
101	4	1	9	35	0
102	4	1	9	36	0
103	4	2	1	37	0
104	4	2	1	38	0
105	4	2	1	39	0
106	4	2	1	40	0
107	4	2	2	41	0
108	4	2	2	42	0
109	4	2	2	43	0
110	4	2	2	44	0
111	4	2	3	45	0
112	4	2	3	46	0
113	4	2	3	47	0
114	4	2	3	48	0
115	4	2	4	49	0
116	4	2	4	50	0
117	4	2	4	51	0
118	4	2	4	52	0
119	4	2	5	53	0
120	4	2	5	54	0
121	4	2	5	55	0
122	4	2	5	56	0
123	4	2	6	57	0
124	4	2	6	58	0
125	4	2	6	59	0
126	4	2	6	60	0
127	4	2	7	61	0
128	4	2	7	62	0
129	4	2	7	63	0
130	4	2	7	64	0
131	4	2	8	65	0
132	4	2	8	66	0
133	4	2	8	67	0
134	4	2	8	68	0
135	4	2	9	69	0
136	4	2	9	70	0
137	4	2	9	71	0
138	4	2	9	72	0
4	1	1	1	4	-1
139	5	1	1	1	1
1	1	1	1	1	0
143	5	1	1	5	0
140	5	1	1	2	0
141	5	1	1	3	0
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_logs (id, user_id, user_name_snapshot, action_type, description, ip_address, created_at) FROM stdin;
24	4	Яшагин Лев	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 15:41:40.012576
25	4	Яшагин Лев	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:41:44.151922
31	4	Яшагин Лев	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:53:47.089207
32	4	Яшагин Лев	VOTE	Участие в голосовании ID 1	127.0.0.1	2026-11-15 15:53:51.973206
38	5	Печкин Георгий	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 15:56:30.975465
39	5	Печкин Георгий	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:56:33.859172
42	4	Яшагин Лев	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:24:11.840215
43	5	Печкин Георгий	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:24:19.168779
44	4	Яшагин Лев	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:29:44.294697
48	5	Печкин Георгий	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:37:56.035775
49	5	Печкин Георгий	UPDATE_PROFILE	Обновлен адрес проживания / статус владельца	127.0.0.1	2026-11-15 16:38:08.777498
4	\N	Пользователев Пользователь	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 14:34:09.837007
5	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:34:13.33451
9	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:00:02.743944
12	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:08:53.455505
13	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:09:15.325395
21	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:29:03.497284
36	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:20.109432
40	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:23:27.224727
45	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:29:58.57389
47	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:34:23.363131
18	\N	Простаков Простак	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 15:21:11.109318
19	\N	Простаков Простак	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:21:16.019384
33	\N	Простаков Простак	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:53:56.54322
37	\N	Простаков Простак	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:27.108358
53	6	Старков Иван	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 16:50:38.819363
54	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:50:43.185661
55	6	Старков Иван	VOTE	Участие в голосовании ID 1	127.0.0.1	2026-11-15 16:50:50.24717
63	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:11:07.601525
67	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:12:18.303606
68	5	Печкин Георгий	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:12:21.727607
69	5	Печкин Георгий	VOTE	Участие в голосовании ID 2	127.0.0.1	2026-11-21 13:12:25.375772
1	\N	Гражданинов Гражданин	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-15 14:22:46.692801
2	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:24:40.437468
3	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:32:22.181346
6	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:34:19.656174
7	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:35:59.080605
8	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 14:37:54.422733
10	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:00:11.209213
11	\N	Гражданинов Гражданин	ADD_BUILDING	Дом по адресу 'ул. 17 Героев, д.1' добавлен, сгенерировано квартир: 40	127.0.0.1	2026-11-15 15:00:50.618919
14	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:14:54.477425
15	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:18:26.919252
16	\N	Гражданинов Гражданин	ADD_BUILDING	Дом по адресу 'ул. Ершова, д.10' добавлен, квартир: 24	127.0.0.1	2026-11-15 15:19:19.853791
17	\N	Гражданинов Гражданин	EDIT_BUILDING	Обновлены данные дома ID 2	127.0.0.1	2026-11-15 15:19:55.914064
20	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:21:32.334923
22	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:29:39.217275
23	\N	Гражданинов Гражданин	ADD_BUILDING	Добавлен дом 'ул. Садовая, д. 11' (генерация квартир: False)	127.0.0.1	2026-11-15 15:33:36.188162
26	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:42:05.868777
27	\N	Гражданинов Гражданин	EDIT_BUILDING	Обновлены данные дома ID 3	127.0.0.1	2026-11-15 15:42:17.520079
28	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:52:32.994661
29	\N	Гражданинов Гражданин	CREATE_POLL	Создано голосование ID 1	127.0.0.1	2026-11-15 15:53:31.291016
30	\N	Гражданинов Гражданин	VOTE	Участие в голосовании ID 1	127.0.0.1	2026-11-15 15:53:38.361473
34	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:05.649943
35	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 15:54:13.882002
41	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:23:31.406491
46	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:30:57.411247
52	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:48:39.606606
56	\N	Гражданинов Гражданин	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:51:58.739257
57	\N	Гражданинов Гражданин	ADD_BUILDING	Добавлен дом 'ул. Пушкина, д.1' (генерация квартир: True)	127.0.0.1	2026-11-15 16:53:02.027657
58	\N	Гражданинов Гражданин	DELETE_MESSAGE	Удалено сообщение ID 2 в чате дома ID 2	127.0.0.1	2026-11-15 16:53:59.638188
59	\N	Гражданинов Гражданин	ADD_BUILDING	Добавлен дом 'Управляющая компания' (генерация квартир: False)	127.0.0.1	2026-11-15 16:55:00.968907
50	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:38:24.283019
61	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:55:44.212305
62	\N	Пользователев Пользователь	UPDATE_PROFILE	Обновлен адрес проживания / статус владельца	127.0.0.1	2026-11-15 16:57:14.943349
64	\N	Пользователев Пользователь	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:11:11.89715
65	\N	Пользователев Пользователь	CREATE_POLL	Создано голосование ID 2	127.0.0.1	2026-11-21 13:11:54.204397
66	\N	Пользователев Пользователь	VOTE	Участие в голосовании ID 2	127.0.0.1	2026-11-21 13:12:01.936279
51	\N	Простаков Простак	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-15 16:47:53.698376
60	\N	Гражданинов Гражданин	CHANGE_PASSWORD	Пользователь сменил пароль в профиле	127.0.0.1	2026-11-15 16:55:35.561644
70	4	Яшагин Лев	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:21:48.445535
71	7	Сапелкин Андрей	REGISTER	Успешная регистрация нового жильца	127.0.0.1	2026-11-21 13:39:14.116751
72	7	Сапелкин Андрей	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:39:17.121898
73	7	Сапелкин Андрей	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:40:14.695486
74	7	Сапелкин Андрей	CHANGE_ROLE	Изменена роль для пользователя ID 7	127.0.0.1	2026-11-21 13:40:35.170374
75	7	Сапелкин Андрей	CHANGE_ROLE	Изменена роль для пользователя ID 6	127.0.0.1	2026-11-21 13:40:43.563109
76	7	Сапелкин Андрей	OWNER_REQUEST_APPROVED	Одобрена заявка на статус собственника для Старков Иван Владимирович (ID 6, ул. Ершова, д.10, кв. 2)	127.0.0.1	2026-11-21 13:40:46.683261
77	7	Сапелкин Андрей	OWNER_REQUEST_APPROVED	Одобрена заявка на статус собственника для Печкин Георгий Ираклиевич (ID 5, ул. 17 Героев, д.1, кв. 1)	127.0.0.1	2026-11-21 13:40:47.837281
78	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 13:41:33.66116
79	7	Сапелкин Андрей	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 14:25:05.15334
80	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 14:25:18.468891
81	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 14:25:18.555372
82	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 14:25:26.814287
83	6	Старков Иван	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 14:35:02.381706
84	7	Сапелкин Андрей	LOGIN	Успешная авторизация в системе	127.0.0.1	2026-11-21 14:38:34.858034
\.


--
-- Data for Name: buildings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.buildings (id, address, floors_count, entrances_count, apartments_count, total_residents) FROM stdin;
1	ул. 17 Героев, д.1	5	2	40	0
2	ул. Ершова, д.10	6	1	24	0
3	ул. Садовая, д. 11	1	1	0	0
4	ул. Пушкина, д.1	9	2	72	0
5	Управляющая компания	9	1	5	0
\.


--
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.messages (id, sender_id, building_id, recipient_id, content, created_at, is_edited) FROM stdin;
4	6	\N	4	Привет, сосед, го на рыбалку на выходных?!	2026-11-15 16:51:49.556041	f
\.


--
-- Data for Name: poll_options; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.poll_options (id, poll_id, option_text) FROM stdin;
1	1	Да
2	1	Нет
3	2	За
4	2	Против
\.


--
-- Data for Name: polls; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.polls (id, title, description, building_id, created_by, expires_at, is_anonymous, is_active, is_closed) FROM stdin;
1	Установка шлагбаума на въезде в ЖК		2	\N	2026-11-20 15:00:00	t	f	f
2	Проверка		1	\N	2026-11-23 10:00:00	f	t	f
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

COPY public.users (id, last_name, first_name, middle_name, username, password_hash, apartment_id, role_id, is_owner_requested, is_owner_verified) FROM stdin;
4	Яшагин	Лев	Трофимович	lev.yashagin	scrypt:32768:8:1$myO9JHnVlohGRCEX$eeefcf66459380e2238558aa624fefd2143b71484ad44cec2f51ff03b722a4e808d304d9e7398f7c163aa084b35d48730dae2126e38d8d22237780f33fb93479	42	3	f	f
7	Сапелкин	Андрей	Иванович	admin	scrypt:32768:8:1$7KgV3oQa0fuAarIh$507439bbcebf0629dc0bf20fe69c1d847def7260e6bf67a4fd96605996285594401a80476a0e0438a43cabc17458ddce963d8a27d002dc620debc83b7967fd4f	139	1	f	f
6	Старков	Иван	Владимирович	StaricHOK	scrypt:32768:8:1$0XYyzaDWfSDifbLJ$97c1715bd085c4dee4a6fa12008baaa68a172631b9d1aea6107a1ec3079ca0c5b217979270c2b5c7b6530795c57fafefe0522eb2705fc226a2d02929586e040e	43	2	f	t
5	Печкин	Георгий	Ираклиевич	georgiy02031979	scrypt:32768:8:1$DMY7kodrtI34OchQ$64d9488bb87ddb7ab5f1d7792fa7a3ac50b1c8f88d59111fe56162c5ceea0c1d171f17da7b84804ea1cc75bb1af890ecd6464462ea28f17dcd949ca0e6792886	1	3	f	t
\.


--
-- Data for Name: votes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.votes (id, poll_id, user_id, option_id, voted_at) FROM stdin;
2	1	4	1	2026-11-15 15:53:51.966608
3	1	6	2	2026-11-15 16:50:50.240313
5	2	5	3	2026-11-21 13:12:25.363835
\.


--
-- Name: apartments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.apartments_id_seq', 143, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 84, true);


--
-- Name: buildings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.buildings_id_seq', 5, true);


--
-- Name: messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.messages_id_seq', 15, true);


--
-- Name: poll_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.poll_options_id_seq', 4, true);


--
-- Name: polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.polls_id_seq', 2, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_id_seq', 3, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 7, true);


--
-- Name: votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.votes_id_seq', 5, true);


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
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


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
-- Name: idx_messages_building; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_building ON public.messages USING btree (building_id, created_at);


--
-- Name: idx_messages_direct; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_messages_direct ON public.messages USING btree (sender_id, recipient_id, created_at);


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
-- Name: messages messages_building_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_building_id_fkey FOREIGN KEY (building_id) REFERENCES public.buildings(id) ON DELETE CASCADE;


--
-- Name: messages messages_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: messages messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE CASCADE;


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

\unrestrict Lvu2pmceZeAHEuVZ01RomaRhvYV1ZPs5VvVUo1j5T81Ak4dYHOekKrj39NZoi3l

