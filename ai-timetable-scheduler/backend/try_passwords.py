import mysql.connector
from mysql.connector import Error

common_passwords = ["root", "password", "admin", "123456", "mysql", "1234", ""]

print("Testing common MySQL passwords for user 'root'...\n")

found = False
for pwd in common_passwords:
    print(f"Trying password: '{pwd}' ... ", end="")
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=pwd,
            port=3306
        )
        if connection.is_connected():
            print("SUCCESS! ✅")
            print(f"\n>>> THE PASSWORD IS: '{pwd}'")
            found = True
            connection.close()
            break
    except Error as e:
        print("Failed ❌")

if not found:
    print("\n❌ None of the common passwords worked.")
    print("You will need to reset your MySQL root password manually.")
