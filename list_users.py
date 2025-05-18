import sqlite3

def list_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, email, is_admin FROM users')
        users = cursor.fetchall()
        if not users:
            print('No users found.')
        else:
            for user in users:
                print(f'id: {user[0]}, email: {user[1]}, is_admin: {user[2]}')
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    list_users() 