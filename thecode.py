import sqlite3
import psycopg2




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
        cur.close() #this edge case will most likely never happen, users have to be logged in to get here but it somehow came up in testing
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
    
    search = f"%{term}%"

    raise NotImplementedError

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

    #TODO: Finish this function to show purchases and process refunds
     
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
        SELECT id, admin_level, first_name, last_name, username, password
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
        print("3) Refund an item")
        print("4) Exit shop")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            term = input("Enter part of an item name to search: ").strip()
            might_be(fratabase, term)
        elif choice == "2":
            item_name = input("Enter the exact item name to purchase: ").strip()
            purchase(fratabase, user_row, item_name)
        elif choice == "3":
            user_refund(fratabase, user_row)
        elif choice == "4":
            print("Seeya.")
            break
        else:
            print("Invalid choice, try again.")



def admin_panel(fratabase, user_row):
    user_id, admin_level, first_name, last_name, username, password, balance = user_row
    print(f"\n=== Admin Control Panel (logged in as {username}) ===")


    #TODO: Implement admin functions below
    raise NotImplementedError
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
    for row in result:
        print(row)
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
    raise NotImplementedError
    
def admin_rename_user(fratabase):
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
        
    uid, old_username = row
    print(f"Current username: {old_username}")

    new_username = input("Enter new username: ").strip()
    if not new_username:
        print("Username cannot be empty.")
        cur.close()
        return

    # check duplicate username
    cur.execute(
        "SELECT username FROM users_tables WHERE username = ? AND id != ?;",
        (new_username, uid),
    )
    if cur.fetchone():
        print("That username is already taken.")
        cur.close()
        return

    try:
        cur.execute(
            "UPDATE users_tables SET username = ? WHERE id = ?;",
            (new_username, uid),
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
        
    uid, uname, old_balance = row
    print(f"User: {uname}, Current balance: {old_balance}")

    try:
        new_balance = float(input("Enter new balance: ").strip())
    except ValueError:
        print("Invalid balance")
        return
    cur.execute("UPDATE users_tables SET balance = ? WHERE id = ?;", (new_balance, uid))
    fratabase.commit()

def admin_change_item_price_qty(fratabase):
        raise NotImplementedError

    

# ------------- MAIN LOGIN FLOW ------------- #

def main():
    print("=== Welcome to Goon Road  ===")

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
