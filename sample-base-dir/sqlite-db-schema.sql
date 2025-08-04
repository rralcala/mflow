BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "account" (
	"id"	TEXT NOT NULL,
	"country"	TEXT NOT NULL,
	"institution"	TEXT NOT NULL,
	"currency"	TEXT NOT NULL,
	"balance"	TEXT NOT NULL,
	"factor"	TEXT NOT NULL,
	"account_type"	TEXT NOT NULL,
	"liquid"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL DEFAULT 1,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "bond" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"capital"	TEXT NOT NULL,
	"currency"	TEXT NOT NULL,
	"maturity_date"	TEXT NOT NULL,
	"rate"	TEXT NOT NULL,
	"entity"	TEXT NOT NULL,
	"country"	TEXT NOT NULL,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "bond_schedule" (
	"id"	INTEGER NOT NULL,
	"bond_id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"date"	TEXT NOT NULL,
	"amount"	TEXT NOT NULL,
	"paid"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "deposit_certificate" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"capital"	TEXT NOT NULL,
	"currency"	TEXT NOT NULL,
	"maturity_date"	TEXT NOT NULL,
	"rate"	TEXT NOT NULL,
	"entity"	TEXT NOT NULL,
	"country"	TEXT NOT NULL,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "deposit_certificate_schedule" (
	"id"	INTEGER NOT NULL,
	"cd_id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"date"	TEXT NOT NULL,
	"amount"	TEXT NOT NULL,
	"paid"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "history" (
	"date"	TEXT NOT NULL,
	"value"	TEXT NOT NULL,
	"user_id"	INTEGER NOT NULL DEFAULT 1,
	"fixed"	INTEGER NOT NULL DEFAULT 0.0,
	"id"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "instrument" (
	"id"	INTEGER NOT NULL,
	"user_id"	INTEGER NOT NULL,
	"country"	TEXT NOT NULL,
	"location"	TEXT NOT NULL,
	"symbol"	TEXT NOT NULL,
	"factor"	TEXT NOT NULL,
	"qty"	TEXT NOT NULL,
	"dividend"	TEXT NOT NULL,
	"dividend_rate"	TEXT NOT NULL,
	"currency"	TEXT NOT NULL,
	"acquisition_date"	TEXT NOT NULL,
	"acquisition_price"	TEXT NOT NULL,
	"liquid"	INTEGER NOT NULL,
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "payable" (
	"id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	"country"	TEXT NOT NULL,
	"currency"	TEXT NOT NULL,
	"description"	TEXT NOT NULL,
	"due_date"	TEXT NOT NULL,
	"amount"	TEXT NOT NULL,
	"commited"	INTEGER NOT NULL,
	"balance"	TEXT NOT NULL DEFAULT amount,
	"one_off"	INTEGER NOT NULL DEFAULT 0,
	"flow_class"	TEXT NOT NULL DEFAULT 'expense',
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "recurrent" (
	"identifier"	TEXT NOT NULL UNIQUE,
	"parent_asset_id"	TEXT,
	"country"	TEXT NOT NULL,
	"amount"	TEXT NOT NULL,
	"currency"	TEXT NOT NULL,
	"recurrence"	TEXT NOT NULL,
	"start"	TEXT NOT NULL,
	"end"	TEXT NOT NULL,
	"flow_class"	TEXT NOT NULL,
	"rate"	TEXT NOT NULL,
	"user_Id"	INTEGER NOT NULL DEFAULT 1,
	PRIMARY KEY("identifier")
);
CREATE TABLE IF NOT EXISTS "recurrent_transaction" (
	"transaction_id"	INTEGER,
	"parent_id"	TEXT NOT NULL,
	"year_month"	TEXT NOT NULL,
	"description"	TEXT NOT NULL,
	"amount"	TEXT NOT NULL,
	"transaction_date"	TEXT NOT NULL,
	"paid_with"	TEXT NOT NULL,
	"create_date"	TEXT NOT NULL,
	"user_id"	INTEGER NOT NULL DEFAULT 1,
	PRIMARY KEY("transaction_id" AUTOINCREMENT)
);
CREATE INDEX IF NOT EXISTS "account_user_id" ON "account" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "bond_schedule_user_bond" ON "bond_schedule" (
	"bond_id",
	"user_id"
);
CREATE INDEX IF NOT EXISTS "bond_schedule_user_id" ON "bond_schedule" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "bond_user_id" ON "bond" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "history_date_user_id" ON "history" (
	"id",
	"date"
);
CREATE INDEX IF NOT EXISTS "history_user_Id" ON "history" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "payable_user_id" ON "payable" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "recurrent_transaction_user_id" ON "recurrent_transaction" (
	"user_id"
);
CREATE INDEX IF NOT EXISTS "recurrent_transaction_user_parent" ON "recurrent_transaction" (
	"parent_id",
	"user_id"
);
CREATE INDEX IF NOT EXISTS "recurrent_user_id" ON "recurrent" (
	"user_Id"
);
CREATE INDEX IF NOT EXISTS "user_id" ON "account" (
	"user_id"
);
COMMIT;
