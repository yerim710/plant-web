import sqlite3

def approve_verifications():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        # 승인 대기 중인 모든 신청을 승인 처리
        cursor.execute('''
            UPDATE admin_verifications 
            SET status = 'approved' 
            WHERE status = 'pending'
        ''')
        conn.commit()
        print('모든 승인 대기 중인 신청이 승인 처리되었습니다.')
    except Exception as e:
        print('Error:', e)
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    approve_verifications() 