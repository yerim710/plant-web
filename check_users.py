import sqlite3

def check_users():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # users 테이블의 모든 레코드 조회
        cursor.execute('SELECT id, name, email FROM users')
        users = cursor.fetchall()
        
        if not users:
            print("등록된 사용자가 없습니다.")
        else:
            print("\n등록된 사용자 목록:")
            print("-" * 50)
            print(f"{'ID':<5} {'이름':<10} {'이메일':<30}")
            print("-" * 50)
            for user in users:
                print(f"{user[0]:<5} {user[1]:<10} {user[2]:<30}")
        
        conn.close()
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    check_users() 