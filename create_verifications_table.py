import sqlite3

def create_verifications_table():
    conn = sqlite3.connect('volunteer.db')
    cursor = conn.cursor()
    try:
        # admin_verifications 테이블 생성
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            organization_name TEXT NOT NULL,
            organization_type TEXT NOT NULL,
            manager_name TEXT NOT NULL,
            manager_phone TEXT NOT NULL,
            manager_email TEXT NOT NULL,
            address TEXT NOT NULL,
            postcode TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            main_activities TEXT NOT NULL,
            business_registration TEXT,
            status TEXT DEFAULT 'pending',
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        conn.commit()
        print('admin_verifications 테이블이 생성되었습니다.')
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    create_verifications_table() 