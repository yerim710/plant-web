import sqlite3

def list_users_verifications():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, user_id, organization, status, created_at 
            FROM admin_verifications
        ''')
        verifications = cursor.fetchall()
        if not verifications:
            print('신청 내역이 없습니다.')
        else:
            print('\n=== 모든 신청 내역 ===')
            for v in verifications:
                print(f'ID: {v[0]}, 사용자ID: {v[1]}, 단체명: {v[2]}, 상태: {v[3]}, 신청일: {v[4]}')
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    list_users_verifications() 