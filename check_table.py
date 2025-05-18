import sqlite3

def check_table():
    conn = sqlite3.connect('volunteer.db')
    cursor = conn.cursor()
    try:
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\n=== 테이블 목록 ===")
        for table in tables:
            print(f"\n테이블: {table[0]}")
            # 각 테이블의 구조 확인
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  컬럼: {col[1]} ({col[2]})")
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    check_table() 