import sqlite3

def check_user(email):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # users 테이블 확인
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    if user:
        print(f"Users 테이블에서 발견: {user}")
    else:
        print("Users 테이블에서 발견되지 않음")
    
    # admins 테이블 확인
    cursor.execute("SELECT * FROM admins WHERE email = ?", (email,))
    admin = cursor.fetchone()
    if admin:
        print(f"Admins 테이블에서 발견: {admin}")
    else:
        print("Admins 테이블에서 발견되지 않음")
    
    conn.close()

if __name__ == "__main__":
    check_user('yerim8896@naver.com') 