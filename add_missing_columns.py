import sqlite3

def add_missing_columns():
    conn = sqlite3.connect('volunteer.db')
    cursor = conn.cursor()
    try:
        # 누락된 컬럼들 추가
        columns = [
            "ADD COLUMN main_activities TEXT",
            "ADD COLUMN business_registration TEXT",
            "ADD COLUMN status TEXT DEFAULT 'pending'",
            "ADD COLUMN rejection_reason TEXT",
            "ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ]
        
        for column in columns:
            try:
                cursor.execute(f"ALTER TABLE admin_verifications {column}")
                print(f"컬럼 추가 성공: {column}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"컬럼이 이미 존재함: {column}")
                else:
                    raise e
        
        conn.commit()
        print("\n모든 컬럼이 추가되었습니다.")
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    add_missing_columns() 