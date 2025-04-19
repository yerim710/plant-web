import sqlite3

def delete_user(email):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # 사용자 삭제
        cursor.execute('DELETE FROM users WHERE email = ?', (email,))
        
        if cursor.rowcount > 0:
            print(f"'{email}' 사용자가 성공적으로 삭제되었습니다.")
        else:
            print(f"'{email}' 사용자를 찾을 수 없습니다.")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    # 삭제할 사용자의 이메일
    email_to_delete = "yerim8896@naver.com"
    delete_user(email_to_delete) 