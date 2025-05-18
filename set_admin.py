import sqlite3

def set_admin():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_admin=1 WHERE email='admin@test.com'")
        conn.commit()
        print('admin@test.com 계정에 관리자 권한을 부여했습니다.')
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    set_admin() 