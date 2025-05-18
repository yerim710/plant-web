import sqlite3

def list_verifications():
    conn = sqlite3.connect('volunteer.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, organization_name, manager_name, status, created_at 
            FROM admin_verifications 
            WHERE status = 'pending'
        ''')
        verifications = cursor.fetchall()
        if not verifications:
            print('승인 대기 중인 신청이 없습니다.')
        else:
            print('\n=== 승인 대기 중인 신청 목록 ===')
            for v in verifications:
                print(f'ID: {v[0]}, 단체명: {v[1]}, 담당자: {v[2]}, 신청일: {v[4]}')
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    list_verifications() 