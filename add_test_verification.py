import sqlite3
from datetime import datetime

def add_test_verification():
    conn = sqlite3.connect('volunteer.db')
    cursor = conn.cursor()
    try:
        # 테스트 데이터 추가
        cursor.execute('''
        INSERT INTO admin_verifications (
            user_id,
            organization_name,
            organization_type,
            manager_name,
            manager_phone,
            manager_email,
            address,
            postcode,
            main_activities,
            status,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            9,  # admin@test.com의 user_id
            '테스트 봉사단체',
            '비영리단체',
            '홍길동',
            '010-1234-5678',
            'test@example.com',
            '서울시 강남구 테헤란로 123',
            '06234',
            '노인 돌봄, 환경 보호 봉사',
            'pending',
            datetime.now()
        ))
        conn.commit()
        print('테스트 승인 신청이 추가되었습니다.')
    except Exception as e:
        print('Error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    add_test_verification() 