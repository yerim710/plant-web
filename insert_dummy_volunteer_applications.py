import sqlite3
import random
from datetime import datetime, timedelta

# 데이터베이스 연결
conn = sqlite3.connect('volunteer.db')
cursor = conn.cursor()

# 더미 데이터 생성
def generate_dummy_applications(num_applications=10):
    # 봉사활동 ID 목록 가져오기
    cursor.execute("SELECT id FROM volunteers")
    volunteer_ids = [row[0] for row in cursor.fetchall()]
    
    # 상태 옵션 - 모두 pending으로 설정
    status = 'pending'
    performance_status = 'pending'
    
    # 더미 데이터 생성
    for i in range(num_applications):
        volunteer_id = random.choice(volunteer_ids)
        user_id = random.randint(1, 10)  # 사용자 ID는 1-10 사이
        applicant_name = f"신청자{i+1}"
        applicant_email = f"applicant{i+1}@example.com"
        
        # 봉사 날짜 (현재로부터 1-30일 사이)
        volunteer_date = (datetime.now() + timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        
        # 데이터 삽입
        cursor.execute("""
            INSERT INTO volunteer_applications 
            (user_id, volunteer_id, applicant_name, applicant_email, volunteer_date, 
             status, rejection_reason, performance_status, performance_rejection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, volunteer_id, applicant_name, applicant_email, volunteer_date,
              status, None, performance_status, None))

# 기존 데이터 삭제
cursor.execute('DELETE FROM volunteer_applications')

# 더미 데이터 삽입 실행
generate_dummy_applications()

# 변경사항 저장 및 연결 종료
conn.commit()
conn.close()

print("더미 데이터가 성공적으로 추가되었습니다. (10개의 대기 상태 신청)") 