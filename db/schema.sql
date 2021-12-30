--
-- PostgreSQL database cluster dump
--

SET default_transaction_read_only = off;

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;



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


ALTER DATABASE jtl_report OWNER TO postgres;


CREATE SCHEMA jtl;

ALTER SCHEMA jtl OWNER TO postgres;


CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;



CREATE TYPE public.data_type AS ENUM (
    'kpi',
    'error',
    'monitoring_logs'
);

ALTER TYPE public.data_type OWNER TO postgres;



CREATE TYPE public.item_status AS ENUM (
    '0',
    '1',
    '2',
    '3',
    '10'
);


ALTER TYPE public.item_status OWNER TO postgres;


CREATE TYPE public.report_status AS ENUM (
    'in_progress',
    'error',
    'ready'
);

ALTER TYPE public.report_status OWNER TO postgres;


SET default_tablespace = '';

SET default_with_oids = false;



CREATE TABLE jtl.samples (
    "timestamp" timestamp without time zone NOT NULL,
    elapsed integer,
    label text,
    success boolean,
    bytes integer,
    sent_bytes integer,
    connect integer,
    hostname text,
    status_code text,
    all_threads integer,
    grp_threads integer,
    latency integer,
    response_message text,
    item_id uuid,
    sut_hostname text
);

ALTER TABLE jtl.samples OWNER TO postgres;



CREATE TABLE jtl.monitor (
    "timestamp" timestamp without time zone NOT NULL,
    cpu numeric,
    mem numeric,
    name text,
    item_id uuid
);

ALTER TABLE jtl.monitor OWNER TO postgres;


CREATE TABLE jtl.api_tokens (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    token character varying(100),
    description character varying(200) NOT NULL,
    created_by uuid NOT NULL,
    create_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

ALTER TABLE jtl.api_tokens OWNER TO postgres;



CREATE TABLE jtl.charts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    plot_data jsonb,
    item_id uuid
);

ALTER TABLE jtl.charts OWNER TO postgres;



CREATE TABLE jtl.data (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    item_data jsonb NOT NULL,
    item_id uuid NOT NULL,
    data_type public.data_type
);

ALTER TABLE jtl.data OWNER TO postgres;


CREATE TABLE jtl.item_stat (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    item_id uuid NOT NULL,
    stats jsonb NOT NULL,
    overview jsonb,
    sut jsonb
);

ALTER TABLE jtl.item_stat OWNER TO postgres;



CREATE TABLE jtl.items (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    note character varying(150),
    environment character varying(100),
    upload_time timestamp without time zone DEFAULT now(),
    start_time timestamp without time zone,
    duration integer,
    scenario_id uuid NOT NULL,
    base boolean,
    status public.item_status DEFAULT '10'::public.item_status,
    hostname character varying(200),
    report_status public.report_status DEFAULT 'ready'::public.report_status NOT NULL,
    threshold_result jsonb,
    is_running boolean DEFAULT false
);

ALTER TABLE jtl.items OWNER TO postgres;



CREATE TABLE jtl.notifications (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    url character varying(400) NOT NULL,
    scenario_id uuid NOT NULL,
    type text NOT NULL
);

ALTER TABLE jtl.notifications OWNER TO postgres;


CREATE TABLE jtl.projects (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_name character varying(50) NOT NULL
);

ALTER TABLE jtl.projects OWNER TO postgres;



CREATE TABLE jtl.scenario (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(50) NOT NULL,
    project_id uuid NOT NULL,
    threshold_enabled boolean DEFAULT false NOT NULL,
    threshold_error_rate numeric DEFAULT 5 NOT NULL,
    threshold_percentile numeric DEFAULT 5 NOT NULL,
    threshold_throughput numeric DEFAULT 5 NOT NULL,
    analysis_enabled boolean DEFAULT true NOT NULL
);

ALTER TABLE jtl.scenario OWNER TO postgres;



CREATE TABLE jtl.share_tokens (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    token text NOT NULL,
    name character varying(200),
    item_id uuid NOT NULL
);

ALTER TABLE jtl.share_tokens OWNER TO postgres;


CREATE TABLE jtl.user_item_chart_settings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    item_id uuid,
    chart_settings jsonb NOT NULL
);

ALTER TABLE jtl.user_item_chart_settings OWNER TO postgres;



CREATE TABLE jtl.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    username character varying(100),
    password character varying(100),
    create_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

ALTER TABLE jtl.users OWNER TO postgres;



ALTER TABLE ONLY jtl.api_tokens
    ADD CONSTRAINT api_tokens_pkey PRIMARY KEY (id);



ALTER TABLE ONLY jtl.api_tokens
    ADD CONSTRAINT api_tokens_token_key UNIQUE (token);


ALTER TABLE ONLY jtl.charts
    ADD CONSTRAINT charts_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.item_stat
    ADD CONSTRAINT item_stat_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.projects
    ADD CONSTRAINT projects_project_name_key UNIQUE (project_name);


ALTER TABLE ONLY jtl.scenario
    ADD CONSTRAINT scenario_pkey PRIMARY KEY (id);

ALTER TABLE ONLY jtl.share_tokens
    ADD CONSTRAINT share_tokens_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.user_item_chart_settings
    ADD CONSTRAINT user_item_chart_settings_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.user_item_chart_settings
    ADD CONSTRAINT user_item_chart_settings_user_id_item_id_constraint UNIQUE (user_id, item_id);


ALTER TABLE ONLY jtl.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


ALTER TABLE ONLY jtl.users
    ADD CONSTRAINT users_username_key UNIQUE (username);



CREATE INDEX data_item_id_index ON jtl.data USING btree (item_id);


CREATE INDEX generator_monitor_timestamp_idx ON jtl.monitor USING btree ("timestamp" DESC);



CREATE INDEX item_stat_item_id_index ON jtl.item_stat USING btree (item_id);



CREATE INDEX items_id_scenario_id_index ON jtl.items USING btree (id, scenario_id);


CREATE INDEX projects_id_project_name_index ON jtl.projects USING btree (id, project_name);



CREATE INDEX samples_elapsed_idx ON jtl.samples USING btree (elapsed);


CREATE INDEX samples_item_idx ON jtl.samples USING btree (item_id);


CREATE INDEX samples_timestamp_idx ON jtl.samples USING btree ("timestamp" DESC);


CREATE INDEX scenario_id_project_id_name_index ON jtl.scenario USING btree (id, project_id, name);


CREATE INDEX share_tokens_item_id_index ON jtl.share_tokens USING btree (item_id);



CREATE UNIQUE INDEX user_item_chart_settings_user_id_item_id_key ON jtl.user_item_chart_settings USING btree (user_id, item_id);



ALTER TABLE ONLY jtl.api_tokens
    ADD CONSTRAINT api_tokens_created_by_fkey FOREIGN KEY (created_by) REFERENCES jtl.users(id) ON DELETE CASCADE;



ALTER TABLE ONLY jtl.charts
    ADD CONSTRAINT charts_item_id_fkey FOREIGN KEY (item_id) REFERENCES jtl.items(id) ON DELETE CASCADE;



ALTER TABLE ONLY jtl.data
    ADD CONSTRAINT data_item_id_fkey FOREIGN KEY (item_id) REFERENCES jtl.items(id) ON DELETE CASCADE;



ALTER TABLE ONLY jtl.monitor
    ADD CONSTRAINT generator_monitor_item_id_fkey FOREIGN KEY (item_id) REFERENCES jtl.items(id) ON DELETE CASCADE;


ALTER TABLE ONLY jtl.item_stat
    ADD CONSTRAINT item_stat_item_id_fkey FOREIGN KEY (item_id) REFERENCES jtl.items(id) ON DELETE CASCADE;



ALTER TABLE ONLY jtl.items
    ADD CONSTRAINT items_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES jtl.scenario(id) ON DELETE CASCADE;



ALTER TABLE ONLY jtl.notifications
    ADD CONSTRAINT notifications_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES jtl.scenario(id);



ALTER TABLE ONLY jtl.samples
    ADD CONSTRAINT samples_item_id_fkey FOREIGN KEY (item_id) REFERENCES jtl.items(id) ON DELETE CASCADE;



ALTER TABLE ONLY jtl.scenario
    ADD CONSTRAINT scenario_project_id_fkey FOREIGN KEY (project_id) REFERENCES jtl.projects(id) ON DELETE CASCADE;



ALTER TABLE ONLY jtl.share_tokens
    ADD CONSTRAINT share_tokens_item_id_fkey FOREIGN KEY (item_id) REFERENCES jtl.items(id) ON DELETE CASCADE;


ALTER TABLE ONLY jtl.user_item_chart_settings
    ADD CONSTRAINT user_item_chart_settings_item_id_fkey FOREIGN KEY (item_id) REFERENCES jtl.items(id) ON DELETE CASCADE;


ALTER TABLE ONLY jtl.user_item_chart_settings
    ADD CONSTRAINT user_item_chart_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES jtl.users(id) ON DELETE CASCADE;


select * from pg_extension;



SELECT public.create_hypertable('jtl.samples', 'timestamp');
SELECT public.create_hypertable('jtl.monitor', 'timestamp');
