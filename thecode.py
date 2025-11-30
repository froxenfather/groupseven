import psycopg2

# ------------- DB CONNECTION ------------- #

def get_connection():
    """
    Update these values for your own database.
    """
    return psycopg2.connect(
        dbname="project_final",
        user="postgres",
        password="Fratabase",
        host="localhost",
        port=5432,
    )

# ------------- USER HELPERS ------------- #

def get_user_by_username(conn, username):
    """
    return ONE user by name.
    users_tables schema:
        id, admin_level, first_name, last_name, username, password
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, admin_level, first_name, last_name, username, password
            FROM users_tables
            WHERE username = %s;
            """,
            (username,),
        )
        return cur.fetchone()


def create_user(conn, first_name, last_name, username, password):
    """
    make a new user with admin level = 0 and minimal info.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users_tables (admin_level, first_name, last_name, username, password)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, admin_level, first_name, last_name, username;
            """,
            (0, first_name, last_name, username, password),
        )
        row = cur.fetchone()
    conn.commit()
    return row  

# ------------- MODES ------------- #

def shop_mode(user_row):
    user_id, admin_level, first_name, last_name, username, _ = user_row
    print(f"\nWelcome to the shop, {username}!")
    print("w2orking on the shop now.\n")


def admin_panel(user_row):
    user_id, admin_level, first_name, last_name, username, _ = user_row
    print(f"\nAdmin Control Panel - User: {username}")
    print("workin on admin stuf now.\n")


def handle_admin_user(user_row):
    """
    Show menu for admin (admin_level == 1).
    """
    while True:
        print("\nYou are an admin.")
        print("1) Shop")
        print("2) Admin Control Panel")
        print("3) Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            shop_mode(user_row)
        elif choice == "2":
            admin_panel(user_row)
        elif choice == "3":
            print("Aight.")
            break
        else:
            print("Invalid choice. Try again.")


# ------------- MAIN LOGIN FLOW ------------- #

def main():
    print("=== Welcome to Goon Road  ===")

    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    fratabase = None
    try:
        fratabase = get_connection()

        user_row = get_user_by_username(fratabase, username)

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
                # new_user does not include the password, so fetch fresh row if needed
                user_row = get_user_by_username(fratabase, username)
                # Non-admin goes directly to shop
                shop_mode(user_row)
            else:
                print("No account created. Exiting.")
                return

        else:
            # User exists, check password
            db_user_id, db_admin_level, db_first, db_last, db_username, db_password = user_row

            if password != db_password:
                print("\nIncorrect password. Access denied.")
                return

            print(f"\nLogin successful. Welcome back, {db_username}!")

            if db_admin_level == 1:
                handle_admin_user(user_row)
            else:
                # Regular user
                shop_mode(user_row)

    except psycopg2.Error as e:
        print("Database error:", e)
    finally:
        if fratabase is not None:
            fratabase.close()


if __name__ == "__main__":
    main()
