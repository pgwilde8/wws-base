-- Master Broker Directory: source of truth for broker MC → contact info.
-- Run on your PostgreSQL DB (e.g. psql -f sql/create_webwise_brokers.sql).

CREATE SCHEMA IF NOT EXISTS webwise;

CREATE TABLE IF NOT EXISTS webwise.brokers (
    mc_number   VARCHAR(20) PRIMARY KEY,
    dot_number  VARCHAR(20),
    company_name VARCHAR(255),
    dba_name    VARCHAR(255),
    website     VARCHAR(255),
    primary_email VARCHAR(255),
    primary_phone VARCHAR(50),
    fax         VARCHAR(50),
    phy_street  VARCHAR(255),
    phy_city    VARCHAR(100),
    phy_state   VARCHAR(50),
    phy_zip     VARCHAR(20),
    rating      DECIMAL(3,2),
    source      VARCHAR(50) DEFAULT 'FMCSA',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_brokers_primary_email ON webwise.brokers(primary_email);
CREATE INDEX IF NOT EXISTS idx_brokers_company_name ON webwise.brokers(company_name);
