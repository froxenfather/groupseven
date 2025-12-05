PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS bigitemtotal (
    item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name   TEXT NOT NULL,
    store       TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    price_item       REAL NOT NULL,
    rating      REAL
);

CREATE TABLE IF NOT EXISTS users_tables (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_level INTEGER      NOT NULL,
    first_name  TEXT,
    last_name   TEXT,
    username    TEXT  NOT NULL UNIQUE,
    password    TEXT  NOT NULL,
    balance     REAL  NOT NULL DEFAULT 100.0 CHECK (balance >= 0)
);

CREATE TABLE IF NOT EXISTS purchases (
    purchase_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER      NOT NULL,
    item_id      INTEGER      NOT NULL,
    quantity     INTEGER      NOT NULL CHECK (quantity > 0),
    final_price  REAL         NOT NULL CHECK (final_price >= 0),
    purchased_at TEXT         NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_purchases_user
        FOREIGN KEY (user_id)
        REFERENCES users_tables(id),

    CONSTRAINT fk_purchases_item
        FOREIGN KEY (item_id)
        REFERENCES bigitemtotal(item_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users_tables(id),
    item_id     INTEGER NOT NULL REFERENCES bigitemtotal(item_id),
    rating      REAL   NOT NULL CHECK (rating >= 0 AND rating <= 5),
    comment     TEXT,
    created_at  TEXT   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_user_item_review UNIQUE (user_id, item_id)
);
