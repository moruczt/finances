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

INSERT INTO accounts (name, side) VALUES ('mbh', 'Assets');

INSERT INTO accounts (name, side) VALUES ('erste', 'Assets');

UPDATE alembic_version SET version_num='51c89b0f8966' WHERE alembic_version.version_num = '33d155bc3dda';

-- Running upgrade 51c89b0f8966 -> 43bc8e612bb7

truncate table accounts restart identity cascade;

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (1, NULL, 'Liquid', 'Assets', 'Assets:Liquid');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (2, 1, 'ErsteDebit', 'Assets', 'Assets:Liquid:ErsteDebit');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (3, 1, 'ErsteHitel', 'Assets', 'Assets:Liquid:ErsteHitel');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (4, 1, 'ErsteWizz', 'Assets', 'Assets:Liquid:ErsteWizz');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (5, 1, 'MbhDebit', 'Assets', 'Assets:Liquid:MbhDebit');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (6, 1, 'MbhCredit', 'Assets', 'Assets:Liquid:MbhCredit');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (7, 1, 'LloydsDebit', 'Assets', 'Assets:Liquid:LloydsDebit');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (8, 1, 'OtpSzep', 'Assets', 'Assets:Liquid:OtpSzep');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (9, 1, 'RevoHUF', 'Assets', 'Assets:Liquid:RevoHUF');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (10, 1, 'RevoGBP', 'Assets', 'Assets:Liquid:RevoGBP');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (11, 1, 'RevoEUR', 'Assets', 'Assets:Liquid:RevoEUR');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (12, 1, 'Cash', 'Assets', 'Assets:Liquid:Cash');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (13, 1, 'Wise', 'Assets', 'Assets:Liquid:Wise');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (14, NULL, 'Investment', 'Assets', 'Assets:Investment');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (15, 14, 'ErsteBroker', 'Assets', 'Assets:Investment:ErsteBroker');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (16, 14, 'Binance', 'Assets', 'Assets:Investment:Binance');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (17, 14, 'Mak', 'Assets', 'Assets:Investment:Mak');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (18, 14, 'OtpLtp', 'Assets', 'Assets:Investment:OtpLtp');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (19, NULL, 'Receiveables', 'Assets', 'Assets:Receiveables');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (20, 19, 'Tibi', 'Assets', 'Assets:Receiveables:Tibi');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (21, 19, 'Anya', 'Assets', 'Assets:Receiveables:Anya');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (22, 19, 'Clift', 'Assets', 'Assets:Receiveables:Clift');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (23, NULL, 'StudentLoan', 'Liabilities', 'Liabilities:StudentLoan');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (24, NULL, 'OpeningBalance', 'Equity', 'Equity:OpeningBalance');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (25, NULL, 'Salary', 'Income', 'Income:Salary');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (26, NULL, 'Clift', 'Income', 'Income:Clift');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (27, NULL, 'Stat', 'Income', 'Income:Stat');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (28, NULL, 'Other', 'Income', 'Income:Other');

INSERT INTO accounts (id, parent_id, name, side, path) VALUES (29, NULL, 'Uncategorised', 'Expenses', 'Expenses:Uncategorised');

SELECT setval(pg_get_serial_sequence('accounts','id'), (select max(id) from accounts));

UPDATE alembic_version SET version_num='43bc8e612bb7' WHERE alembic_version.version_num = '51c89b0f8966';

COMMIT;

