import sqlite3

def check_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    users = c.fetchall()
    print("\n=== Users ===")
    for user in users:
        print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Password: {user[3]}")
    conn.close()

if __name__ == '__main__':
    check_users() 