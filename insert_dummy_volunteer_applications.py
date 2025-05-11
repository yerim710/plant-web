import sqlite3
from datetime import datetime

conn = sqlite3.connect('volunteer.db')
c = conn.cursor()

# 1. 기존 데이터 삭제
c.execute('DELETE FROM volunteer_applications')

# 2. 임시 데이터 삽입
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
dummy_data = [
    (1, 4, '임시 관리자', 'admin@test.com', '2024-08-15', now, 'pending'),
    (2, 4, '테스터1', 'tester1@test.com', '2024-08-15', now, 'pending'),
    (3, 5, '테스터2', 'tester2@test.com', '2024-08-15', now, 'pending'),
    (4, 5, '테스터3', 'tester3@test.com', '2024-08-16', now, 'pending'),
    (5, 8, '테스터4', 'tester4@test.com', '2024-08-17', now, 'pending'),
]
for user_id, volunteer_id, name, email, vdate, appdate, status in dummy_data:
    c.execute('''
        INSERT INTO volunteer_applications (
            user_id, volunteer_id, applicant_name, applicant_email, volunteer_date, application_date, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, volunteer_id, name, email, vdate, appdate, status))

conn.commit()
conn.close()
print('임시 데이터 삭제 및 5건 삽입 완료') 