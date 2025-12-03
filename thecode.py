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
    """
      Purchase flow:
    - find all items with this exact name
    - show cheapest, most expensive, highest rated
    - let user pick 1/2/3 or 4 for all others
    - ask for quantity
    - check stock and user balance
    - insert into purchases, update stock, subtract from user
    """

    #TODO: Implement purchase function: this one is big
    user_id, admin_level, first_name, last_name, username, password, balance = user_row

    raise NotImplementedError

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
