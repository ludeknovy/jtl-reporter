CREATE EXTENSION "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS jtl;

CREATE TABLE jtl.projects(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_name character varying(50) NOT NULL UNIQUE
);

CREATE TABLE jtl.items (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    test_name character varying(40) NOT NULL,
    project_id uuid NOT NULL REFERENCES jtl.projects(id),
    jtl_data jsonb NOT NULL,
    note character varying(150),
    environment character varying(20),
    upload_time timestamp without time zone DEFAULT now(),
    start_time timestamp without time zone,
    duration integer
);

CREATE TABLE jtl.item_stat (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    item_id uuid NOT NULL REFERENCES jtl.items(id),
    stats jsonb NOT NULL
);

