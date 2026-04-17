BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 973d4b7da83f

CREATE TYPE accountside AS ENUM ('Assets', 'Liabilities', 'Income', 'Expenses', 'Equity');

CREATE TABLE accounts (
    id SERIAL NOT NULL, 
    parent_id INTEGER, 
    name VARCHAR(100) NOT NULL, 
    side accountside NOT NULL, 
    path VARCHAR(255), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(parent_id) REFERENCES accounts (id), 
    UNIQUE (path)
);

CREATE TABLE transactions (
    id SERIAL NOT NULL, 
    date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    description VARCHAR(255), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

CREATE INDEX ix_transactions_date ON transactions (date);

CREATE TABLE account_configs (
    id SERIAL NOT NULL, 
    account_id INTEGER, 
    parser VARCHAR(100) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id)
);

CREATE TABLE raw_imports (
    id SERIAL NOT NULL, 
    account_id INTEGER, 
    raw_data JSON NOT NULL, 
    row_hash VARCHAR(64), 
    source_filename VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id)
);

CREATE UNIQUE INDEX ix_raw_imports_row_hash ON raw_imports (row_hash);

CREATE TABLE rule (
    id SERIAL NOT NULL, 
    account_id INTEGER NOT NULL, 
    target_account_id INTEGER NOT NULL, 
    conditions JSON NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id), 
    FOREIGN KEY(target_account_id) REFERENCES accounts (id)
);

CREATE TABLE entries (
    id SERIAL NOT NULL, 
    transaction_id INTEGER NOT NULL, 
    account_id INTEGER NOT NULL, 
    raw_import_id INTEGER, 
    amount_huf NUMERIC(20, 4) NOT NULL, 
    amount_orig NUMERIC(20, 4) NOT NULL, 
    exchange_rate NUMERIC(20, 4) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id), 
    FOREIGN KEY(raw_import_id) REFERENCES raw_imports (id), 
    FOREIGN KEY(transaction_id) REFERENCES transactions (id)
);

INSERT INTO alembic_version (version_num) VALUES ('973d4b7da83f') RETURNING alembic_version.version_num;

-- Running upgrade 973d4b7da83f -> 33d155bc3dda

ALTER TABLE accounts ADD COLUMN test VARCHAR(100);

INSERT INTO accounts (name, side, test) VALUES ('mbh', 'Assets', 'asd');

INSERT INTO accounts (name, side, test) VALUES ('erste', 'Assets', 'dsa');

UPDATE alembic_version SET version_num='33d155bc3dda' WHERE alembic_version.version_num = '973d4b7da83f';

-- Running upgrade 33d155bc3dda -> 51c89b0f8966

ALTER TABLE accounts DROP COLUMN test;

UPDATE alembic_version SET version_num='51c89b0f8966' WHERE alembic_version.version_num = '33d155bc3dda';

COMMIT;

FAILED: Using --sql with --autogenerate does not make any sense
