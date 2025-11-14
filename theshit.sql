CREATE TABLE bigitemtotal (
    item_id      SERIAL PRIMARY KEY,
    item_name   VARCHAR(255) NOT NULL,
    store       VARCHAR(100) NOT NULL,
    price_item   DECIMAL(10,2) NOT NULL,
    rating      DECIMAL(3,2)
);


CREATE TABLE