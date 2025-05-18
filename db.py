import sqlite3
import os
from werkzeug.security import generate_password_hash

class Database:
    def __init__(self):
        self.db_path = 'users.db'
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # admins 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_confirmed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 테스트용 관리자 계정 추가 (비밀번호: admin123)
        hashed_password = generate_password_hash('admin123')
        cursor.execute('''
            INSERT OR IGNORE INTO admins (email, password, is_confirmed)
            VALUES (?, ?, ?)
        ''', ('admin@test.com', hashed_password, True))
        
        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def execute_query(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    def raw_query(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close() 