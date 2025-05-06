import sqlite3
from werkzeug.security import generate_password_hash
import os

# 데이터베이스 파일 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
USERS_DB_PATH = os.path.join(current_dir, 'users.db')

ADMIN_EMAIL = 'admin@test.com'
ADMIN_PASSWORD = 'admin123'
ADMIN_NAME = 'Admin User'

conn = None
try:
    print(f"Connecting to database: {USERS_DB_PATH}")
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()

    # 1. 기존 admin@test.com 계정 삭제 시도
    print(f"Attempting to delete existing user: {ADMIN_EMAIL}")
    cursor.execute("DELETE FROM users WHERE email = ?", (ADMIN_EMAIL,))
    print(f"Deleted {cursor.rowcount} existing rows for {ADMIN_EMAIL}.")

    # 2. 새로운 admin@test.com 계정 생성 (해시된 비밀번호 사용)
    print(f"Generating password hash for: {ADMIN_PASSWORD}")
    hashed_pw = generate_password_hash(ADMIN_PASSWORD)
    print(f"Inserting new user: {ADMIN_EMAIL} with name: {ADMIN_NAME}")
    cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", 
                   (ADMIN_NAME, ADMIN_EMAIL, hashed_pw))
    conn.commit()
    print(f"Successfully inserted new admin user with ID: {cursor.lastrowid}")

except sqlite3.Error as e:
    print(f"Database error: {e}")
    if conn:
        conn.rollback()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if conn:
        conn.close()
        print("Database connection closed.") 