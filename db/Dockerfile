FROM timescale/timescaledb-ha:pg16.4-ts2.16.1-all
ENV POSTGRES_DB jtl_report
COPY schema.sql /docker-entrypoint-initdb.d/
