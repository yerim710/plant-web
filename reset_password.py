import sqlite3
from werkzeug.security import generate_password_hash

def reset_password(email, new_password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # 새로운 비밀번호 해시 생성
    password_hash = generate_password_hash(new_password)
    
    # users 테이블에서 비밀번호 업데이트
    cursor.execute("UPDATE users SET password = ? WHERE email = ?", (password_hash, email))
    
    if cursor.rowcount > 0:
        print(f"비밀번호가 성공적으로 재설정되었습니다.")
        print(f"새로운 해시: {password_hash}")
    else:
        print(f"해당 이메일({email})을 찾을 수 없습니다.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset_password('yerim8896@naver.com', 'yerim0710!') 