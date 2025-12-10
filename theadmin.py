import sqlite3
import psycopg2
import pandas as pd

# ------------- DB CONNECTION ------------- #

def get_connection():
    return sqlite3.connect("fratabase.db")

# ------------- BULK LOADING ------------- #

def load_csv_to_bigitemtotal(
    fratabase,
    csv_path,
    store_name,
    name_col,
    qty_col = None,
    price_col = None,
    rating_col=None,
    encoding="utf-8",
):

    print(f"\nLoading {csv_path} for store={store_name} ...")

    #Read the CSV

    df = pd.read_csv(csv_path, encoding=encoding)

    # Bare Minimum Colums required: throw error if it doesnt have these
    if name_col not in df.columns:
        raise ValueError(f"{csv_path}: missing item name column '{name_col}'")

    if price_col is None or price_col not in df.columns:
        raise ValueError(f"{csv_path}: missing price column '{price_col}'")
    


    #Only selct the barebones fellas
    cols = [name_col, price_col]
    if qty_col is not None and qty_col in df.columns:
        cols.append(qty_col)
    if rating_col is not None and rating_col in df.columns:
        cols.append(rating_col)

    df = df[cols].copy()

    #Rename to Internal Names
    rename_map = {name_col: "item_name", price_col: "price_item"}
    if qty_col is not None and qty_col in df.columns:
        rename_map[qty_col] = "quantity"
    if rating_col is not None and rating_col in df.columns:
        rename_map[rating_col] = "rating"

    df.rename(columns=rename_map, inplace=True)

    #Add store name
    df["store"] = store_name

    # Quantity must be integer and at least 1
    if qty_col and qty_col in df.columns:
        df["quantity"] = (pd.to_numeric(df[qty_col], errors="coerce"))
        df["quantity"] = df["quantity"].fillna(10)
    else:
        df["quantity"] = 10 #default fallback value is 10

    df["quantity"] = df["quantity"].clip(lower=1).astype(int)

    # Price must be positive float
    if df[price_col].astype(str).str.contains("₹").any():
        is_rupees = True
    else:
        is_rupees = False
    
    df["price_item"] = (
    df["price_item"]
    .astype(str)
    .str.replace(r"[^\d.\-]", "", regex=True)   # keep digits, dot, minus
)
    
    df["price_item"] = (
        pd.to_numeric(df["price_item"], errors="coerce")
        .fillna(0)
        .clip(lower=0.01)
    )
    if is_rupees:
        INR_TO_USD = 0.011
        df["price_item"] = df["price_item"] * INR_TO_USD
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    else:
        df["rating"] = None

    #Drop rows
    df = df[
        df["item_name"].notna()
        & (df["item_name"].astype(str).str.strip() != "")
    ]

    df = df[df["item_name"].str.strip() != ""]

    rows = df[["item_name", "store", "quantity", "price_item", "rating"]].itertuples(index=False, name=None)

    
    cur = fratabase.cursor()
    cur.executemany(
        "INSERT INTO bigitemtotal (item_name, store, quantity, price_item, rating) VALUES (?, ?, ?, ?, ?);",
        list(rows),
    )
    fratabase.commit()
    cur.close()
    print(f"Inserted {len(df)} rows from {csv_path}.")


# Loading specific datasets

def seed_bigitemtotal():
    """
    Run this ONCE after downloading all CSVs locally.
    Adjust paths & column names to match each dataset.
    """
    conn = get_connection()
    cur = conn.cursor()

    conn.commit()

    # === 1) E-commerce data (carrie1/ecommerce-data) ===
    # Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country

    '''
    load_csv_to_bigitemtotal(
        conn,
        csv_path="data/ecommerce-data.csv",   # <- path where you saved it
        store_name="Ecommerce",
        name_col="Description",
        qty_col="Quantity",
        price_col="UnitPrice",
        rating_col=None,
        encoding="latin1",  # often needed for this dataset
    )
    '''

    # === 2) Amazon Sales Dataset ===
    # Open it once in a small script or notebook and run: print(df.columns)
    # Then plug the correct names below — here are COMMON patterns, but you must check:
    # e.g. 'product_name', 'rating', 'discounted_price', etc.
    load_csv_to_bigitemtotal(
        conn,
        csv_path="data/amazon.csv",
        store_name="Amazon",
        name_col="product_name",
        qty_col= None,
        price_col="discounted_price", # or 'actual_price' – depends on dataset
        rating_col="rating",          # or whatever the rating column is called
    )

        # === 3) Target Store Dataset ===
    # This dataset might be store locations, not items. If there's no product info,
    # you may NOT want to load it into bigitemtotal at all, or you need a different table.
    # If there IS a product/price table, map it here like the others.

    # Example (ONLY if the CSV actually has these):
    # load_csv_to_bigitemtotal(
    #     conn,
    #     csv_path="data/target_items.csv",
    #     store_name="Target",
    #     name_col="product_name",
    #     qty_col="quantity",
    #     price_col="unit_price",
    #     rating_col=None,
    # )

        # === 4) Walmart Sales (mikhail1681/walmart-sales) ===
    # Depending on the file, you may have item name + sales; check df.columns.
    # For pure time series (no item name), this may not belong in bigitemtotal at all.
    # Example if there IS an item-level file:
    # load_csv_to_bigitemtotal(
    #     conn,
    #     csv_path="data/walmart_items.csv",
    #     store_name="Walmart",
    #     name_col="item_name",
    #     qty_col="quantity",
    #     price_col="price",
    #     rating_col=None,
    # )

if __name__ == "__main__":
    seed_bigitemtotal()

