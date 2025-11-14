CREATE TABLE bigitemtotal (
    item_id      SERIAL PRIMARY KEY,
    item_name   VARCHAR(255) NOT NULL,
    store       VARCHAR(100) NOT NULL,
    price_item   DECIMAL(10,2) NOT NULL,
    rating      DECIMAL(3,2)
);


CREATE table users_tables(
    id SERIAL PRIMARY KEY,
    admin_level INTEGER NOT NULL,
    first_name VARCHAR(20),
    last_name VARCHAR(20),
    username VARCHAR(10) PRIMARY KEY,
    password VARCHAR(10) PRIMARY KEY
)
    admin_level 
    -- first 
    -- last
    -- username
    -- passsword
);
