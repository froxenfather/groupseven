CREATE TABLE bigitemtotal (
    itemid      SERIAL PRIMARY KEY,
    item_name   VARCHAR(255) NOT NULL,
    store       VARCHAR(100) NOT NULL,
    priceItem   DECIMAL(10,2) NOT NULL,
    rating      DECIMAL(3,2)
);