import sqlite3
import psycopg2
import pandas as pd




#TODO: Fill in all the functions marked with TODO
#TODO: Fulll the database somehow with items and such
# ------------- DB CONNECTION ------------- #

def get_connection():
    return sqlite3.connect("fratabase.db")


# ------------- USER HELPERS ------------- #

def get_unc(fratabase, username):
    """
    tester function
    return ONE user by name.
    users_tables schema:
        id, admin_level, first_name, last_name, username, password, balance
    """
    cur = fratabase.cursor()
    cur.execute(
        """
        SELECT id, admin_level, first_name, last_name, username, password, balance
        FROM users_tables
        WHERE username = ?;
        """,
        (username,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def create_user(fratabase, first_name, last_name, username, password):
    with fratabase:
        cur = fratabase.cursor()
        cur.execute("""
            INSERT INTO users_tables (admin_level, first_name, last_name, username, password, balance)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (0, first_name, last_name, username, password, 100))

        user_id = cur.lastrowid

        cur.execute("""
            SELECT id, admin_level, first_name, last_name, username, password, balance
            FROM users_tables
            WHERE id = ?;
        """, (user_id,))
        return cur.fetchone() 

# ------------------------------------------------------------- PURCHASE FRENGINE --------------------------------------------------------------- #
def purchase(fratabase, user_row, item_name):

    #the fragnum opus reveals itself
    """
    Purchase flow (SQLite version):
    - find all items with this exact name
    - show cheapest, most expensive, highest rated
    - let user pick 1/2/3 or 4 for all others
    - ask for quantity
    - check stock and user balance
    - insert into purchases, update stock, subtract from user
    - kill myself over the genuine fifty edge cases
    """
    user_id, admin_level, first_name, last_name, username, password, balance = user_row

    cur = fratabase.cursor()

    # 1. Find all items with this exact name, use might_be to browse but dont want 

    #Trying with the a might_be style search instead
    item_name = "%?%",{item_name}

    cur.execute(
        """
        SELECT item_id, item_name, store, quantity, price_item, rating
        FROM bigitemtotal
        WHERE item_name = ?
        """,
        (item_name,),
    )
    allburgers = cur.fetchall()

    if not allburgers:
        print(f"\nNo items found with name '{item_name}'.\n")
        cur.close()
        return

    IDX_ID = 0
    IDX_NAME = 1 #pretty sure i didnt even need these man
    IDX_STORE = 2
    IDX_QTY = 3
    IDX_PRICE = 4
    IDX_RATING = 5

    # 2. derive cheapest, most expensive, highest rated
    cheapburger = min(allburgers, key=lambda r: r[IDX_PRICE]) #had to look up lambda functions again lmfao
    expensiveburger = max(allburgers, key=lambda r: r[IDX_PRICE])

    def rating_or_zero(row): #helper function to avoid none type errors because that was a huge proble
        return row[IDX_RATING] if row[IDX_RATING] is not None else 0
    #note this doesnt actually set any reviews to zero it just makes it so they are the lowest possible value when comparing for max

    reviewburger = max(allburgers, key=lambda r: (rating_or_zero(r), -r[IDX_PRICE]))

    # remove duplicates (same item could be multiple categories)
    id_map_main = {}
    for r in (cheapburger, expensiveburger, reviewburger):
        id_map_main[r[IDX_ID]] = r #map rules dont allow for duplicates thus why im doing this lmao
        #it literally just does all this for me :)

    def print_option(label, row): #helpr function because there are jst so many fucking options
        iid, name, store, qty, price, rating = row
        print(
            f"{label}) ID {iid} | {name} | Store: {store} | " #row was too long man
            f"Qty: {qty} | Price: {price:.2f} | Rating: {rating if rating is not None else 'N/A'}"
        )

    print(f"\nOptions for '{item_name}':")
    print_option("1 (cheapest)", cheapburger)
    print_option("2 (most expensive)", expensiveburger)
    print_option("3 (highest rated)", reviewburger)
    print("4) See ALL matching items") #im out here thrwoing ass

    froice = None

    # 3. Let them pick main options or "all"
    while True:
        choice = input("Choose 1, 2, 3, 4 or 'cancel': ").strip().lower()
        if choice == "cancel":
            print("Purchase cancelled.")
            cur.close()
            return
        if choice in {"1", "2", "3"}:
            mapping = {"1": cheapburger, "2": expensiveburger, "3": reviewburger}
            froice = mapping[choice] #easy way for me to jork it basically make a disctionary
            break
        if choice == "4":
            break
        print("Invalid choice.")

    # 4. If 4: show all items and choose by item_id
    if froice is None:
        print("\nAll matching items:")
        the_frictionary = {} #map item id to row for easy lookup later
        for row in allburgers: #pretty f print the rest of the rows with f print
            #might wanna turn this to pandas?
            iid, name, store, qty, price, rating = row
            the_frictionary[iid] = row #map the idtem id to the row for easy lookup later
            print(f"ID {iid} | {name} | Store: {store} | Qty: {qty} | Price: {price:.2f} | Rating: {rating if rating is not None else 'N/A'}")

        while True: #loop through items
            item_id_froice = input("Enter item ID to buy, or 'cancel': ").strip().lower()
            if item_id_froice == "cancel":
                print("Purchase cancelled.")
                cur.close() #return to shop cleanly and close cursor bc sqlite can leak memory
                return
            try:
                sel_id = int(item_id_froice) #make sure we dont do any weird shit with letters
            except ValueError:
                print("Not a valid integer ID.")
                continue
            if sel_id in the_frictionary:
                froice = the_frictionary[sel_id]
                break
            else:
                print("No item with that ID in the list.")

    # unpack selected item
    item_id, name, store, quantity, price, rating = froice

    if quantity <= 0:
        print("\nThat item is out of stock.\n")
        cur.close()
        return

    # 5. ask for quantity
    while True:
        qty_str = input(f"Enter quantity to buy (available {quantity}), or 'cancel': ").strip().lower()
        if qty_str == "cancel":
            print("Purchase cancelled.")
            cur.close()
            return
        try:
            qty = int(qty_str)
        except ValueError:
            print("Quantity must be an integer.")
            continue
        if qty <= 0:
            print("Quantity must be positive.")
            continue
        if qty > quantity: #what an awesome fking line
            print("Not enough in stock.")
            continue #edge cases again 
        break

    total_burger = qty * float(price) #compute price

    # 6. recheck balance from DB
    cur.execute("SELECT balance FROM users_tables WHERE id = ?;", (user_id,))
    row = cur.fetchone()
    if row is None:
        print("Error: user not found when checking balance.")
        cur.close() #allah must intervene for this edge case to trigger
        return

    current_balance = float(row[0])

    print(f"\nCurrent balance: {current_balance:.2f}")
    print(f"Cost for {qty} x {name} at ${price:.2f} each: ${total_burger:.2f}")

    if total_burger > current_balance:
        print("You do not have enough balance.")
        cur.close() #edge case gain
        return

    confirm = input("Proceed with purchase? (y/n): ").strip().lower()
    if confirm not in {"y", "yes"}:
        print("Purchase cancelled.") #im edging
        cur.close()
        return

    new_balance = current_balance - total_burger #causes errors somtimes might make float

    # 7. commit changes: update balance, stock, insert purchase
    try:
        #okay so we update user balance
        cur.execute(
            "UPDATE users_tables SET balance = ? WHERE id = ?;",
            (new_balance, user_id),
        )

        #then we update stock
        cur.execute(
            "UPDATE bigitemtotal SET quantity = quantity - ? WHERE item_id = ?;",
            (qty, item_id),
        )

        #and FINALLY insert into purchases
        cur.execute(
            """
            INSERT INTO purchases (user_id, item_id, quantity, final_price)
            VALUES (?, ?, ?, ?);
            """,
            (user_id, item_id, qty, total_burger),
        )

        fratabase.commit()
        print(f"\nPurchase successful! New balance: {new_balance:.2f}\n")

    except Exception as e:
        fratabase.rollback()
        print("Database error during purchase:", e)

    finally:
        cur.close() #do not forget to do ts

    #this program honestly took me the beter half of yesterday to write ngl
    #most of it was just strIGHT edge cases
    

# ------------------------------------------------------------- SEARCH FRENGINE --------------------------------------------------------------- #
def might_be(fratabase, term):
    """  
    Find all items with names similar to search_term and print a nice list.
    Returns the list of rows.
    1) Use SQL LIKE with %term% to find similar names
    2) Print a numbered list of results with name, price, quantity, avg rating"""
    #TODO: Implement might_be function
    term = term.strip()
    search = f"%{term}%"

    cur = fratabase.cursor()
    cur.execute("SELECT * FROM bigitemtotal WHERE item_name LIKE ?;", (search,))

    result = cur.fetchall()
    df = pd.DataFrame(result, columns=[desc[0] for desc in cur.description])
    if df.empty:
        print("no results...")
    else:
        print(df)

        #good work jiah

    cur.close()

# --------------------------------------------- REVIEW FRENGINE --------------------------------------------------------------- #

def review_item(fratabase, user_row):
    """
    Let a user choose one of their purchases and leave a rating + comment.
    Then recompute average rating per item from reviews and update bigitemtotal.
    """
    user_id, admin_level, first_name, last_name, username, password, balance = user_row

    cur = fratabase.cursor()

    # 1. just like refund grab users purchases
    cur.execute(
        """
        SELECT p.purchase_id,
               p.item_id,
               b.item_name,
               p.quantity,
               p.final_price,
               p.purchased_at
        FROM purchases p
        JOIN bigitemtotal b ON p.item_id = b.item_id
        WHERE p.user_id = ?
        ORDER BY p.purchased_at DESC;
        """,
        (user_id,),
    )
    rows = cur.fetchall()

    if not rows:
        print(f"\nUser '{username}' has no purchases to review.\n")
        cur.close()
        return

    print(f"\nRecent purchases for {username}:")
    print("ID | Item              | Qty | Total   | When")
    print("---+-------------------+-----+---------+---------------------")
    for pid, item_id, item_name, qty, total, ts in rows:
        print(f"{pid:<3} | {item_name[:19]:<19} | {qty:>3} | {float(total):>7.2f} | {ts}")

    # 2.choose purchase to review
    while True:
        choice = input("\nEnter purchase_id to review (or 'cancel'): ").strip().lower()
        if choice == "cancel":
            print("Review cancelled.")
            cur.close()
            return
        try:
            purchase_id = int(choice)
            break
        except ValueError:
            print("purchase_id must be an integer.")

    # 3. Re-fetch that purchase and validate ownership just like in purchase and refund
    cur.execute(
        """
        SELECT p.purchase_id,
               p.item_id,
               b.item_name
        FROM purchases p
        JOIN bigitemtotal b ON p.item_id = b.item_id
        WHERE p.purchase_id = ?
          AND p.user_id = ?;
        """,
        (purchase_id, user_id),
    )
    row = cur.fetchone()

    if row is None:
        print("No such purchase exists with that ID for this user.")
        cur.close()
        return

    _, item_id, item_name = row
    print(f"\nYou are reviewing: {item_name} (item_id {item_id})")

    # 4. Get rating 1–5 (decimals allowed)
    while True:
        rating_str = input("Enter rating (1.0 to 5.0, decimals allowed): ").strip()
        try:
            rating = float(rating_str)
        except ValueError:
            print("Rating must be a number.")
            continue
        if rating < 1.0 or rating > 5.0:
            print("Rating must be between 1.0 and 5.0.")
            continue
        break

    # 5. Get optional text review
    comment = input("Enter a short written review (or press Enter to skip): ").strip()
    if comment == "":
        comment = None

    try:
        # 6. Insert the review row
        cur.execute(
            """
            INSERT INTO reviews (user_id, item_id, rating, comment)
            VALUES (?, ?, ?, ?);
            """,
            (user_id, item_id, rating, comment),
        )

        # 7. the big scary one: recompute average ratings for all items and update bigitemtotal
        # this BETTER be good enough for you all 
        cur.execute(
            """
            WITH per_item AS (
                SELECT
                    item_id,
                    AVG(rating) AS avg_rating,
                    COUNT(*)    AS num_reviews
                FROM reviews
                WHERE rating IS NOT NULL
                GROUP BY item_id
            ),
            joined AS (
                SELECT
                    b.item_id,
                    b.rating       AS old_rating,
                    p.avg_rating   AS new_rating,
                    p.num_reviews
                FROM bigitemtotal b
                JOIN per_item p ON b.item_id = p.item_id
            ),
            affected AS (
                SELECT item_id, new_rating
                FROM joined
                WHERE new_rating IS NOT NULL
            )
            UPDATE bigitemtotal
            SET rating = (
                SELECT new_rating
                FROM affected
                WHERE affected.item_id = bigitemtotal.item_id
            )
            WHERE item_id IN (SELECT item_id FROM affected);
            """
        )

        fratabase.commit()
        print(f"\nThanks for reviewing {item_name}! Rating saved and item averages updated.\n")

    except Exception as e:
        fratabase.rollback()
        print("Error while saving review and updating ratings:", e)

    finally:
        cur.close()



# ------------------------------------------------------------- REFUND FRENGINE --------------------------------------------------------------- #
def refund(fratabase, user_row):

    """
    Global refund engine.

    Takes:
        fratabase: psycopg2 connection
        user_row: (id, admin_level, first_name, last_name, username, password, balance)

    Shows that user's purchases, asks which purchase_id to refund,
    and performs: balance +, stock +, delete purchase row. then ads the balance back to user
    """
     

    user_id, admin_level, first_name, last_name, username, password, balance = user_row

    cur = fratabase.cursor()
    cur.execute(
        """
        SELECT p.purchase_id, p.item_id, b.item_name,
            p.quantity, p.final_price, p.purchased_at
        FROM purchases p
        JOIN bigitemtotal b ON p.item_id = b.item_id
        WHERE p.user_id = ?
        ORDER BY p.purchased_at DESC;
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()

    if not rows: #no purchases avaliable
        print(f"\nUser '{username}' has no purchases to refund.\n")
        return


    #the next four lines might have been shamelessly generated by chatgpt
    #i really must learn to use pd.df more often
    print(f"\nRecent purchases for {username}:")
    print("ID | Item              | Qty | Total   | When")
    print("---+-------------------+-----+---------+---------------------")
    for pid, item_id, item_name, qty, total, ts in rows:
        print(f"{pid:<3} | {item_name[:19]:<19} | {qty:>3} | {float(total):>7.2f} | {ts}") #syntax sugar, thank you chatgpt

    #choose which purchase to refund
    while True:
        choice = input("\nEnter purchase_id to refund (or 'cancel'): ").strip().lower()
        if choice == "cancel":
            print("Refund cancelled.")
            return
        try:
            purchase_id = int(choice)
            break
        except ValueError:
            print("purchase_id must be an integer.")

    # re-fetch that one purchase and validate ownership
    cur = fratabase.cursor()
    cur.execute(
        """
        SELECT p.purchase_id,
               p.item_id,
               b.item_name,
               p.quantity,
               p.final_price
        FROM purchases p
        JOIN bigitemtotal b ON p.item_id = b.item_id
        WHERE p.purchase_id = ?
          AND p.user_id = ?;
        """,
        (purchase_id, user_id),
    )
    row = cur.fetchone()

    if row is None:
        print("No such purchase exists with that ID for this user.")
        cur.close()
        return

    burger, item_id, item_name, qty, total_price = row
    total_price = float(total_price)

    print(f"\nRefunding purchase {purchase_id}:")
    print(f"User: {username}")
    print(f"Item: {item_name} (ID {item_id})")
    print(f"Quantity: {qty}")
    print(f"Total price: {total_price:.2f}")

    confirm = input("Proceed with refund? (y/n): ").strip().lower()
    if confirm not in {"y", "yes"}:
        print("Refund cancelled.")
        cur.close()
        return

    try:
        # 1) give money back to guy
        cur.execute(
            "UPDATE users_tables SET balance = balance + ? WHERE id = ?;",
            (total_price, user_id),
        )

        # 2) restock items in bigitemtotal
        cur.execute(
            "UPDATE bigitemtotal SET quantity = quantity + ? WHERE item_id = ?;",
            (qty, item_id),
        )

        # 3) delete purchase be carefull with keys etc
        cur.execute(
            "DELETE FROM purchases WHERE purchase_id = ?;",
            (purchase_id,),
        )

        fratabase.commit()
        print("Refund completed: Yoink.")

    except Exception as e:
        fratabase.rollback()
        print("Error during refund:", e)

    finally:
        cur.close()


     
def user_refund(fratabase, user_row):
    """
    Logged-in user refunds one of THEIR purchases.
    Just calls the global refund engine.
    """
    refund(fratabase, user_row)

def admin_refund(fratabase):
    try:
        user_id = int(input("Enter user ID to refund purchases for: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    cur = fratabase.cursor()
    cur.execute("""
        SELECT id, admin_level, first_name, last_name, username, password, balance
        FROM users_tables
        WHERE id = ?;
    """, (user_id,))
    user_row = cur.fetchone()
    cur.close()

    if user_row is None:
        print("No such user.")
        return

    refund(fratabase, user_row)



# ------------------------------------------------------------- SETTINGS --------------------------------------------------------------- #
def settings(fratabase, user_row): #done i think
    #Show settings menu for changing username/password.
    user_id, admin_level, first_name, last_name, username, password, balance = user_row
    print(f"\n=== Settings for {username} ===")

    while True:
        print("\nSettings options:")
        print("1) Change username")
        print("2) Change password")
        print("3) Back")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            user_row = user_change_username(fratabase, user_row)
        elif choice == "2":
            user_change_password(fratabase, user_row)
        elif choice == "3":
            break
        else:
            print("Invalid choice, try again.")
    return user_row


def user_change_username(fratabase, user_row):
    user_id, admin_level, first_name, last_name, old_username, password, balance = user_row
    new_username = input("Enter new username: ").strip()

    if not new_username:
        print("Username cannot be empty.")
        return user_row

    cur = fratabase.cursor()
    try:
        cur.execute(
            "UPDATE users_tables SET username = ? WHERE id = ?;",
            (new_username, user_id),
        )
        fratabase.commit()
    except sqlite3.Error as e:
        fratabase.rollback()
        cur.close()
        print("Could not update username:", e)
        return user_row

    print(f"Username changed from '{old_username}' to '{new_username}'.")

    cur.execute(
        """
        SELECT id, admin_level, first_name, last_name, username, password, balance
        FROM users_tables
        WHERE id = ?;
        """,
        (user_id,),
    )
    new_row = cur.fetchone()
    cur.close()
    return new_row if new_row is not None else user_row



def user_change_password(fratabase, user_row):
    user_id, admin_level, first_name, last_name, username, password, balance = user_row

    current = input("Enter current password: ").strip()

    if current != password:
        print("Current password is incorrect.")
        return

    new1 = input("Enter new password: ").strip()
    new2 = input("Confirm new password: ").strip()

    if new1 != new2:
        print("Passwords do not match.")
        return

    cur = fratabase.cursor()
    try:
        cur.execute("SELECT password FROM users_tables WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        if row is None:
            print("User not found in database.")
            return
        if current != row[0]:
            print("Current password is incorrect.")
            return

        cur.execute(
            "UPDATE users_tables SET password = ? WHERE id = ?;",
            (new1, user_id),
        )
        fratabase.commit()
        print("Password updated.")
    finally:
        cur.close()

    #call me john copy and paste





# ------------------------------------------------------------- MODES --------------------------------------------------------------- #

def user_mode(fratabase, user_row):
    user_id, admin_level, first_name, last_name, username, password, balance = user_row
    print(f"\nWelcome, {username}!")

    while True:
        print("\nWhat would you like to do?")
        print("1) Shop")
        print("2) Settings")
        print("3) Exit shop")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            shop_mode(fratabase, user_row)
        elif choice == "2":
            print("Seeya.")
            user_row =settings(fratabase, user_row)
        elif choice == "3":
            print("Seeya.")
            break
        else:
            print("Invalid choice, try again.")


def shop_mode(fratabase, user_row):
    user_id, admin_level, first_name, last_name, username, password, balance = user_row
    print(f"\nWelcome to the shop, {username}!")

    while True:
        print("\nWhat would you like to do?")
        print("1) Search items by name (might_be)")
        print("2) Purchase an item by exact name")
        print("3) Leave a review for an item")
        print("4) Refund an item")
        print("5) Exit shop")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            term = input("Enter part of an item name to search: ").strip()
            might_be(fratabase, term)
        elif choice == "2":
            item_name = input("Enter the exact item name to purchase: ").strip()
            purchase(fratabase, user_row, item_name)
        elif choice == "3":
            review_item(fratabase, user_row)
    
        elif choice == "4":
            user_refund(fratabase, user_row)
        elif choice == "5":
            print("Seeya.")
            break
        else:
            print("Invalid choice, try again.")



def admin_panel(fratabase, user_row):
    user_id, admin_level, first_name, last_name, username, password, balance = user_row
    print(f"\n=== Admin Control Panel (logged in as {username}) ===")


    #TODO: Implement admin functions below
    #raise NotImplementedError
    while True:
        print("\nAdmin options:")
        print("1) List all users")
        print("2) Delete a user")
        print("3) Change user admin level")
        print("4) Rename a user")
        print("5) Change user balance")
        print("6) Change item price/quantity")
        print("7) Refund a purchase")
        print("8) Back to previous menu")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            admin_list_users(fratabase)
        elif choice == "2":
            admin_delete_user(fratabase)
        elif choice == "3":
            admin_change_admin_level(fratabase)
        elif choice == "4":
            admin_rename_user(fratabase)
        elif choice == "5":
            admin_change_balance(fratabase)
        elif choice == "6":
            admin_change_item_price_qty(fratabase)
        elif choice == "7":
            admin_refund(fratabase)
        elif choice == "8":
            print("Leaving admin panel.")
            break
        else:
            print("Invalid choice, try again.")

def big_button(conn):
    # this shit is almost directly copied from this cool ass template online i found
    choice = input("Print everything EXCEPT bigitemtotal? (Y/N): ").strip().lower()

    # Get list of all user tables from SQLite
    cur = conn.cursor()
    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table';
    """)
    all_tables = [row[0] for row in cur.fetchall()]

    cur.close()

    # Optionally filter out bigitemtotal
    tables_excluding_big = [t for t in all_tables if t.lower() != "bigitemtotal"]

    if choice == "y":
        tables_to_print = tables_excluding_big
    else:
        tables_to_print = all_tables

    if not tables_to_print:
        print("\nNo tables to print.\n")
        return

    print("\n=== PRINTING TABLES ===\n")

    for table in tables_to_print:
        print(f"\n--- TABLE: {table} ---")
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT * FROM {table};")
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]

            # Header
            header = " | ".join(colnames)
            print(header)
            print("-" * (len(header) + 5))

            # Rows
            if rows:
                for r in rows:
                    print(" | ".join(str(x) for x in r))
            else:
                print("(no rows)")
        except Exception as e:
            print(f"Failed to read {table}: {e}")
        finally:
            cur.close()


# ------------- ADMIN FRENGINE "that one lady that goes how may i direct your call" ------------- #
def handle_admin_user(fratabase,user_row):
    """
    Show menu for admin (admin_level == 1).
    """
    while True:
        print("\nYou are an admin.")
        print("1) Shop")
        print("2) Admin Control Panel")
        print("3) Big Print Button")
        print("4) Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            user_mode(fratabase, user_row)
        elif choice == "2":
            admin_panel(fratabase, user_row)
        elif choice == "3":
            print("BIG boy")
            big_button(fratabase)
        elif choice == "4":
            print("Aight.")
            break
        else:
            print("Invalid choice. Try again.")

def admin_list_users(fratabase):
    cur = fratabase.cursor()
    cur.execute(f"SELECT * FROM users_tables;")
    result = cur.fetchall()
    df = pd.DataFrame(result, columns= ["id", "admin_level", "first_name", "last_name", "username", "password", "balance"])
    print(df)
def admin_delete_user(fratabase):
    admin_list_users(fratabase)
    print("All users have been displayed...")
    choice = input("Enter user ID of user to delete or type C to cancel: ").strip()

    if choice.lower() == "c":
        print("Cancelled.")
        return

    try:
        user_id = int(choice)
    except ValueError:
        print("Invalid ID.")
        return

    cur = fratabase.cursor()
    try:
        cur.execute("DELETE FROM users_tables WHERE id = ?;", (user_id,))
        fratabase.commit()
        print(f"User {user_id} deleted.")
    except sqlite3.Error as e:
        fratabase.rollback()
        print("Failed to delete user:", e)
    finally:
        cur.close()
    
def admin_change_admin_level(fratabase):
    admin_level = -1
    admin_list_users(fratabase)
    print("All users have been displayed...")
    choice = input("Enter user ID of user you want to change admin level (type C to cancel): ").strip()
    if choice.lower() == "c":
        print("Cancelled.")
        return
    while admin_level == -1:
        admin_level = input("Enter 0 for normal user, 1 for admin (type C to cancel): ").strip()
        if admin_level not in ("0", "1", "c", "C"):
            print("Only enter 1, 0, or C, no other values are excepted")
        elif admin_level.lower() == "c":
            print("Cancelled.")
            return

    try:
        user_id = int(choice)
        level = int(admin_level)
    except ValueError:
        print("Invalid ID.")
        return

    cur = fratabase.cursor()
    try:
        cur.execute(f"UPDATE users_tables SET admin_level = {level} WHERE id = {user_id};")
        fratabase.commit()
        print(f"User {user_id} Admin level set to {level}")
    except sqlite3.Error as e:
        fratabase.rollback()
        print("Failed to update user:", e)
    finally:
        cur.close()
def admin_rename_user(fratabase):
    try:
        user_id = int(input("Enter user ID to rename: ").strip())
    except ValueError:
        print("Invalid ID")
        return
    cur = fratabase.cursor()
        
    cur.execute("SELECT id, username, balance FROM users_tables WHERE id = ?;", (user_id,))
    row = cur.fetchone()

    if row is None:
        print("No user found")
        cur.close()
        return
        
    user_id, old_username = row
    print(f"Current username: {old_username}")

    new_username = input("Enter new username: ").strip()
    if not new_username:
        print("Username cannot be empty.")
        cur.close()
        return

    # check duplicate username
    cur.execute(
        "SELECT username FROM users_tables WHERE username = ? AND id != ?;",
        (new_username, user_id),
    )
    if cur.fetchone():
        print("That username is already taken.")
        cur.close()
        return

    try:
        cur.execute(
            "UPDATE users_tables SET username = ? WHERE id = ?;",
            (new_username, user_id),
        )
        fratabase.commit()
        print(f"Username changed from '{old_username}' to '{new_username}'.")
    except sqlite3.Error as e:
        fratabase.rollback()
        print("Failed to rename user:", e)
    finally:
        cur.close()

def admin_change_balance(fratabase): 
    try:
        user_id = int(input("Enter user ID to modify balance: ").strip())
    except ValueError:
        print("Invalid ID")
        return
    cur = fratabase.cursor()
        
    cur.execute("SELECT id, username, balance FROM users_tables WHERE id = ?;", (user_id,))
    row = cur.fetchone()

    if row is None:
        print("No user found")
        cur.close()
        return
        
    user_id, uname, old_balance = row
    print(f"User: {uname}, Current balance: {old_balance}")

    try:
        new_balance = float(input("Enter new balance: ").strip())
    except ValueError:
        print("Invalid balance")
        cur.close()
        return

    try:
        cur.execute(
            "UPDATE users_tables SET balance = ? WHERE id = ?;",
            (new_balance, user_id),
        )
        fratabase.commit()
        print(f"Balance updated: {old_balance} to {new_balance, user_id}")
    except sqlite3.Error as e:
        fratabase.rollback()
        print("Failed to update balance:", e)
    finally:
        cur.close()


def admin_change_item_price_qty(fratabase):
    cur = fratabase.cursor()

    cur.execute("SELECT item_id, item_name, price_item, quantity FROM bigitemtotal;")
    rows = cur.fetchall()

    if not rows:
        print("No items found.")
        cur.close()
        return

    print("\nItems:")
    for item_id, item_name, price_item, quantity in rows:
        print(f"ID number: {item_id} | Item Name: {item_name} | Price: {price_item} | Quantity: {quantity}")
    try:
        item_id = int(input("Input item ID you with to modify").strip())
    except ValueError:
        print("Invalid ID")
        cur.close()
        return

    cur.execute("SELECT item_id, item_name, price_item, quantity FROM bigitemtotal WHERE item_id = ?;", (item_id,),)

    row = cur.fetchone()

    if row is None:
        print("Item not found.")
        cur.close()
        return

    item_id, item_name, old_price, old_quantity = row
    print(f"Item Name: {item_name} | Price: {old_price} | Quantity: {old_quantity}")

    new_price = input("Enter updated price").strip()
    new_quantity = input("Enter updated quantity").strip()

    if new_price == "":
        new_price = old_price
    else:
        try:
            new_price = float(new_price)
        except ValueError:
            print("Invalid price")
            cur.close()
            return

    if new_quantity == "":
        new_quantity = old_quantity
    else:
        try:
            new_quantity = int(new_quantity)
        except ValueError:
            print("Invalid quantity")
            cur.close()
            return         

    try:
        cur.execute(
            "UPDATE bigitemtotal SET price = ?, quantity = ? WHERE item_id = ?;",
            (new_price, new_quantity, item_id)
        )
    
        fratabase.commit()
        print(f"Item: {item_name} Updated price from {old_price} to {new_price} and quantity from {old_quantity} to {new_quantity}")
    except sqlite3.Error as e:
        fratabase.rollback()
        print("Failed to update item price / quantity:", e)
    finally:
        cur.close()

# ------------- MAIN LOGIN FLOW ------------- #

def main():
    print("Welcome to the Shop!")

    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    fratabase = None
    try:
        fratabase = get_connection()

        user_row = get_unc(fratabase, username)

        if user_row is None:
            # user not found, pormpt to make one
            print(f"\nUser '{username}' not found.")
            create_choice = input("Do you want to create a new account with this username? (y/n): ").strip().lower()

            if create_choice == "y":

                print(f"Please Enter your First and Last Name for the new account.")
                first_name = input("First Name: ").strip()
                last_name = input("Last Name: ").strip()
                new_user = create_user(fratabase, first_name, last_name, username, password)
                print(f"Account created successfully. Welcome, {username}!")
                #grab this man
                user_row = get_unc(fratabase, username)
                # Non-admin goes directly to shop
                user_mode(fratabase, user_row)
            else:
                print("No account created. Exiting.")
                return

        else:
            #user exists, check password
            db_user_id, db_admin_level, db_first, db_last, db_username, db_password, db_balance = user_row

            if password != db_password:
                print("\nIncorrect password. Access denied.")
                return

            print(f"\nLogin successful. Welcome back, {db_username}!")

            if db_admin_level == 1:
                handle_admin_user(fratabase,user_row)
            else:
                user_mode(fratabase, user_row)


    except sqlite3.Error as e:
        print("Database error:", e)

    finally:
        if fratabase is not None:
            fratabase.close()


if __name__ == "__main__":
    main()
