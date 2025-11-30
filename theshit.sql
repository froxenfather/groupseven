CREATE TABLE bigitemtotal (
    item_id      SERIAL PRIMARY KEY,
    item_name   VARCHAR(255) NOT NULL,
    store       VARCHAR(100) NOT NULL,
    quantity    INTEGER NOT NULL,
    price_item   DECIMAL(10,2) NOT NULL,
    rating      DECIMAL(3,2)
);


CREATE TABLE users_tables (
    id          SERIAL PRIMARY KEY,
    admin_level INTEGER      NOT NULL,
    first_name  VARCHAR(20),
    last_name   VARCHAR(20),
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL      
    balance DECIMAL(15,2) NOT NULL DEFAULT 100.0 CHECK (bank_balance >= 0   )
);

CREATE TABLE purchases (
    purchase_id  SERIAL PRIMARY KEY,
    user_id      INTEGER      NOT NULL,
    item_id      INTEGER      NOT NULL,
    quantity     INTEGER      NOT NULL CHECK (quantity > 0),
    final_price  DECIMAL(10,2) NOT NULL CHECK (final_price >= 0),
    purchased_at TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_purchases_user
        FOREIGN KEY (user_id)
        REFERENCES users_tables(id),

    CONSTRAINT fk_purchases_item
        FOREIGN KEY (item_id)
        REFERENCES bigitemtotal(item_id)
);


CREATE TABLE reviews (
    review_id   SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users_tables(id),
    item_id     INTEGER NOT NULL REFERENCES bigitemtotal(item_id),
    rating      DECIMAL(3,2) NOT NULL CHECK (rating >= 0 AND rating <= 5),
    comment     TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_user_item_review UNIQUE (user_id, item_id)
);

