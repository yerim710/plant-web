import sqlite3
from werkzeug.security import check_password_hash

def check_password(email, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # users 테이블에서 사용자 정보 조회
    cursor.execute("SELECT id, name, email, password FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if user:
        print(f"사용자 정보:")
        print(f"ID: {user[0]}")
        print(f"이름: {user[1]}")
        print(f"이메일: {user[2]}")
        print(f"저장된 비밀번호 해시: {user[3]}")
        
        # 비밀번호 검증
        is_valid = check_password_hash(user[3], password)
        print(f"\n비밀번호 검증 결과: {'성공' if is_valid else '실패'}")
        
        # 새로운 해시 생성 (비교용)
        from werkzeug.security import generate_password_hash
        new_hash = generate_password_hash(password)
        print(f"\n새로 생성된 해시: {new_hash}")
    else:
        print(f"해당 이메일({email})을 찾을 수 없습니다.")
    
    conn.close()

if __name__ == "__main__":
    check_password('yerim8896@naver.com', 'yerim0710!') 