import sqlite3
import psycopg2
import pandas as pd
import re

# ------------- DB CONNECTION ------------- #

def get_connection():
    return sqlite3.connect("fratabase.db")


# ------------- Name Cleaning------------- #



STOPWORDS = {
    "for", "with", "new", "edition", "pack", "set", "model",
    "the", "and", "of", "a", "an", "in", "to"
}

def clean_catalog_name(name: str, word_limit=6, max_len=40):
    """Clean and shorten product names into catalog-friendly versions."""
    
    if not isinstance(name, str):
        return name

    #remove brackets 
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\[.*?\]", "", name)

    # Remove extra spaces and hyphens
    name = re.sub(r"[^A-Za-z0-9\s\-]", "", name)

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()

    # Remove filler/stop words
    tokens = [t for t in name.split() if t.lower() not in STOPWORDS]

    # Limit to first N meaningful words
    tokens = tokens[:word_limit]

    # If removing stopwords removed everything, fallback
    if not tokens:
        tokens = name.split()[:word_limit]

    # Reconstruct and apply Title Case for catalog style
    name = " ".join(tokens).strip().title()

    return name

# ------------- Remove duplicates ------------- #
def remove_duplicates(fratabase):
    """
    Delete duplicate rows from bigitemtotal, keeping one copy.
    Two rows are considered duplicates if all of these match:
    item_name, store, quantity, price_item, rating.
    """
    cur = fratabase.cursor()

    # Delete any row whose rowid is NOT the minimum for its exact-value group
    cur.execute("""
        DELETE FROM bigitemtotal
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM bigitemtotal
            GROUP BY item_name, store, quantity, price_item, rating
        );
    """)

    deleted = cur.rowcount  # how many rows were removed
    fratabase.commit()
    cur.close()

    print(f"Removed {deleted} exact duplicate rows from bigitemtotal.")
# ------------- BULK LOADING ------------- #

def load_csv_to_bigitemtotal(
    fratabase,
    csv_path,
    store_name = None,
    name_col = None,
    qty_col=None,
    price_col=None,
    rating_col=None,
    store_col = None,
    encoding="utf-8",
):

    print(f"\nLoading {csv_path} for store={store_name} ...")

    # load csv
    df = pd.read_csv(csv_path, encoding=encoding)

    # Bare bones columns required
    if name_col not in df.columns:
        raise ValueError(f"{csv_path}: missing item name column '{name_col}'")

    if price_col is None or price_col not in df.columns:
        raise ValueError(f"{csv_path}: missing price column '{price_col}'")

    # Keep only the needed columns
    cols = [name_col, price_col]
    if qty_col is not None and qty_col in df.columns:
        cols.append(qty_col)
    if rating_col is not None and rating_col in df.columns:
        cols.append(rating_col)

    df = df[cols].copy()

    #Rename to internal names
    rename_map = {name_col: "item_name", price_col: "price_item"}
    if qty_col is not None and qty_col in df.columns:
        rename_map[qty_col] = "quantity"
    if rating_col is not None and rating_col in df.columns:
        rename_map[rating_col] = "rating"

    # --- Store handling ---
    if store_col is not None and store_col in df.columns:
        # Use CSV column for store names
        df["store"] = (
            df[store_col]
            .astype(str)
            .str.strip()
        )
        # Fallback: if some rows have blank/NaN store, use store_name if provided
        if store_name is not None:
            df["store"] = df["store"].where(
                df["store"] != "",       # keep non-empty
                other=store_name        # replace empty with default
            )
            df["store"] = df["store"].fillna(store_name)
    else:
        # No store_col given → use constant store_name for all rows
        if store_name is None:
            raise ValueError(f"{csv_path}: either store_name or store_col must be provided")
        df["store"] = store_name


    df.rename(columns=rename_map, inplace=True)

    #Add store name
    df["store"] = store_name

    #Clean item name
    
    df["item_name"] = df["item_name"].astype(str).apply(clean_catalog_name)

    #Quantity handling (now only use 'quantity')
    if "quantity" in df.columns:
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(10)
    else:
        df["quantity"] = 10  # default fallback

    df["quantity"] = df["quantity"].clip(lower=1).astype(int)

    # Price handling — detect ₹ 
    raw_price = df["price_item"].astype(str)

    is_rupees = raw_price.str.contains("₹").any()

    # strip symbols/extra chars
    df["price_item"] = (
        raw_price
        .str.replace(r"[^\d.\-]", "", regex=True)  # keep digits, dot, minus
        .str.strip()
    )

    df["price_item"] = (
        pd.to_numeric(df["price_item"], errors="coerce")
        .fillna(0)
        .clip(lower=0.01)
    )

    #conversion
    if is_rupees:
        INR_TO_USD = 0.011  
        df["price_item"] = round(df["price_item"] * INR_TO_USD, 2)

    # Rating
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    else:
        df["rating"] = None

    #Drop bad item names
    df = df[
        df["item_name"].notna()
        & (df["item_name"].astype(str).str.strip() != "")
    ]

    #Prepare rows & insert
    rows = df[["item_name", "store", "quantity", "price_item", "rating"]].itertuples(
        index=False, name=None
    )

    cur = fratabase.cursor()
    cur.executemany(
        "INSERT INTO bigitemtotal (item_name, store, quantity, price_item, rating) "
        "VALUES (?, ?, ?, ?, ?);",
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

    # Ecommerce data
    # Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country

    load_csv_to_bigitemtotal(
        conn,
        csv_path="data/ecommerce_data.csv",   # <- path where you saved it
        store_name="Ecommerce",
        name_col="Description",
        qty_col="Quantity",
        price_col="UnitPrice",
        rating_col=None,
        encoding="latin1",  # often needed for this dataset
    )

    # Amazon Sales Dataset

    load_csv_to_bigitemtotal(
        conn,
        csv_path="data/amazon.csv",
        store_name="Amazon",
        name_col="product_name",
        qty_col=None,
        price_col="discounted_price",
        rating_col="rating",          
    )

    # Whole Foods Dataset
    load_csv_to_bigitemtotal(
        conn,
        csv_path="data/whole_foods.csv",
        store_name="Whole Foods",
        name_col="product",
        qty_col=None,
        price_col="regular",
        rating_col=None,
    )
    # Various Grocery Stores Dataset
    load_csv_to_bigitemtotal(
        conn,
        csv_path="data/grocery_chain_data.csv",
        store_name="store_name",
        name_col="product_name",
        qty_col="quantity",
        price_col="unit_price",
        rating_col=None,
    )

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
    remove_duplicates(conn)
if __name__ == "__main__":
    seed_bigitemtotal()

