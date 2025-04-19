from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, send_file
from flask_cors import CORS
import sqlite3
import random
import string
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import base64
import time
import logging
from flask import session
from werkzeug.security import check_password_hash
import pandas as pd
from io import BytesIO

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 현재 디렉토리의 절대 경로를 구합니다
current_dir = os.path.dirname(os.path.abspath(__file__))
logger.debug(f"Current directory: {current_dir}")

app = Flask(__name__, static_folder=current_dir, static_url_path='')
CORS(app)
app.secret_key = 'your-secret-key'  # 세션을 위한 비밀 키

@app.after_request
def after_request(response):
    response.headers.add('ngrok-skip-browser-warning', 'true')
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def home():
    try:
        if 'user_id' in session:
            return redirect(url_for('main_page'))
        return send_from_directory(current_dir, 'login.html')
    except Exception as e:
        logger.error(f"홈 페이지 로드 오류: {str(e)}")
        return send_from_directory(current_dir, 'login.html')

@app.route('/login')
def login_page():
    try:
        if 'user_id' in session:
            return redirect(url_for('main_page'))
        return send_from_directory(current_dir, 'login.html')
    except Exception as e:
        logger.error(f"로그인 페이지 로드 오류: {str(e)}")
        return send_from_directory(current_dir, 'login.html')

@app.route('/signup')
def signup_page():
    try:
        return send_from_directory(current_dir, 'signup.html')
    except Exception as e:
        logger.error(f"회원가입 페이지 로드 오류: {str(e)}")
        return send_from_directory(current_dir, 'signup.html')

@app.route('/main')
def main_page():
    try:
        if 'user_id' not in session:
            return redirect(url_for('home'))
        return send_from_directory(current_dir, 'main.html')
    except Exception as e:
        logger.error(f"메인 페이지 로드 오류: {str(e)}")
        return redirect(url_for('home'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        logger.debug(f"Attempting to serve static file: {filename}")
        return send_from_directory('static', filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {str(e)}")
        return jsonify({'error': f'Failed to load file: {str(e)}'}), 500

# 인증 코드 저장소
verification_codes = {}

# 데이터베이스 초기화 함수
def init_db():
    print("Starting database initialization")
    try:
        # users.db 초기화
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # users 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # verification_codes 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS verification_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_used INTEGER DEFAULT 0
            )
        ''')
        
        # admin_verifications 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS admin_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                organization TEXT NOT NULL,
                representative TEXT NOT NULL,
                business_number TEXT NOT NULL,
                office_phone TEXT NOT NULL,
                address TEXT NOT NULL,
                manager_phone TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("users.db 초기화 완료")
        
        # volunteer.db 초기화
        conn = sqlite3.connect('volunteer.db')
        c = conn.cursor()
        
        # volunteers 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                duration TEXT NOT NULL,
                max_volunteers INTEGER NOT NULL,
                current_volunteers INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # posts 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # volunteer_applications 테이블 생성
        c.execute('''
            CREATE TABLE IF NOT EXISTS volunteer_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,       -- 신청자 ID (users.db의 users 테이블 참조)
                volunteer_id INTEGER NOT NULL,  -- 봉사활동 ID (volunteers 테이블 참조)
                applicant_name TEXT NOT NULL,   -- 신청자 이름 (users 테이블에서 가져옴)
                applicant_email TEXT NOT NULL,  -- 신청자 이메일 (users 테이블에서 가져옴)
                volunteer_date TEXT NOT NULL,   -- 봉사 활동일자 (volunteers 테이블에서 가져옴)
                application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 신청 날짜
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')), -- 신청 상태
                FOREIGN KEY (volunteer_id) REFERENCES volunteers (id)
                -- user_id는 다른 DB 파일이므로 FOREIGN KEY 제약조건은 주석 처리 또는 애플리케이션 레벨에서 관리
                -- FOREIGN KEY (user_id) REFERENCES users (id) 
            )
        ''')
        
        conn.commit()
        conn.close()
        print("volunteer.db 초기화 완료")
        
    except Exception as e:
        print(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
        raise

# 데이터베이스 초기화 실행
init_db()

# 인증 코드 생성 함수
def generate_verification_code():
    # 영문과 숫자 조합으로 6자리 코드 생성
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=6))

# SMTP 설정
SMTP_SERVER = "smtp.naver.com"
SMTP_PORT = 465
SMTP_USERNAME = "yerim8896@naver.com"
SMTP_PASSWORD = "CYV363B6R7TP"

def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            logger.info("SMTP 서버 연결 성공")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            logger.info("SMTP 로그인 성공")
            server.send_message(msg)
            logger.info("이메일 전송 성공")

        return True
    except Exception as e:
        logger.error(f"이메일 전송 오류 상세: {str(e)}")
        return False

# API 엔드포인트 설정
API_BASE_URL = "http://35.232.136.23:5000"

@app.route('/api/send-verification', methods=['POST', 'OPTIONS'])
def send_verification():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
            
        email = data.get('email')
        if not email:
            return jsonify({'success': False, 'message': '이메일을 입력해주세요.'}), 400

        # 인증 코드 생성
        verification_code = generate_verification_code()
        
        # 이메일 전송
        success = send_email(email, "이메일 인증 코드", f"""
        안녕하세요,
        
        요청하신 이메일 인증 코드는 다음과 같습니다:
        
        {verification_code}
        
        이 코드는 5분간 유효합니다.
        
        감사합니다.
        """)
        
        if not success:
            return jsonify({'success': False, 'message': '이메일 전송에 실패했습니다.'}), 400

        # 인증 코드 저장
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO verification_codes (email, code, created_at)
            VALUES (?, ?, ?)
        """, (email, verification_code, datetime.now()))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': '인증 코드가 이메일로 전송되었습니다.'
        })

    except Exception as e:
        logger.error(f"인증 코드 전송 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/verify-code', methods=['POST'])
def verify_code():
    try:
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')
        
        if not all([email, code]):
            return jsonify({'success': False, 'message': '이메일과 인증 코드를 입력해주세요.'}), 400

        # 인증 코드 확인
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("""
            SELECT code, created_at 
            FROM verification_codes 
            WHERE email = ? AND code = ?
        """, (email, code))
        
        result = c.fetchone()
        if not result:
            conn.close()
            return jsonify({'success': False, 'message': '잘못된 인증 코드입니다.'}), 400

        stored_code, created_at = result
        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
        
        # 5분 제한 확인
        if (datetime.now() - created_at).total_seconds() > 300:
            conn.close()
            return jsonify({'success': False, 'message': '인증 코드가 만료되었습니다.'}), 400

        # 인증 완료 후 코드 삭제
        c.execute('DELETE FROM verification_codes WHERE email = ? AND code = ?', (email, code))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': '인증이 완료되었습니다.'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        # 필수 필드 확인
        if not all([name, email, password]):
            return jsonify({'success': False, 'message': '모든 필드를 입력해주세요.'}), 400

        # 이메일 중복 확인
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT email FROM users WHERE email = ?', (email,))
        if c.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': '이미 등록된 이메일입니다.'}), 400

        # 인증 코드 생성 및 전송
        verification_code = generate_verification_code()
        success = send_email(email, "이메일 인증 코드", f"""
        안녕하세요,회원가입해주셔서 감사합니다.
        
        요청하신 이메일 인증 코드는 다음과 같습니다:
        
        {verification_code}
        
        이 코드는 5분간 유효합니다.
        
        감사합니다.
        """)
        
        if not success:
            conn.close()
            return jsonify({'success': False, 'message': '이메일 전송에 실패했습니다.'}), 400
        
        # 인증 코드 저장
        c.execute("""
            INSERT OR REPLACE INTO verification_codes (email, code, created_at)
            VALUES (?, ?, ?)
        """, (email, verification_code, datetime.now()))
        
        # 사용자 등록
        c.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                 (name, email, password))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True, 
            'message': '회원가입이 완료되었습니다. 로그인페이지로 이동해주세요'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin-verification')
def admin_verification():
    user_id = session.get('user_id')
    if not user_id:
        logger.warning("Admin verification page accessed without login, redirecting.")
        return redirect(url_for('login'))

    conn = None
    verification = None
    try:
        logger.debug(f"Fetching admin verification status for user_id: {user_id}")
        conn = sqlite3.connect("users.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, organization, status, created_at 
            FROM admin_verifications 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        verification = cursor.fetchone()
        
        if verification:
             logger.debug(f"Found verification record for user {user_id}: ID={verification['id']}, Status={verification['status']}")
        else:
             logger.debug(f"No verification record found for user {user_id}.")

    except sqlite3.Error as e:
        # Log the full traceback for database errors
        logger.error(f"Database error fetching admin verification for user {user_id}: {str(e)}", exc_info=True)
        verification = None # Ensure verification is None on error
    except Exception as e:
        # Log the full traceback for other errors
        logger.error(f"Server error fetching admin verification for user {user_id}: {str(e)}", exc_info=True)
        verification = None # Ensure verification is None on error
    finally:
        if conn:
            logger.debug(f"Closing database connection for user {user_id}.")
            conn.close()
            
    logger.debug(f"Rendering admin_verification.html for user {user_id}.")
    try:
        # Render the template, passing the potentially None verification object
        return render_template('admin_verification.html', verification=verification)
    except Exception as e:
        # Catch potential Jinja rendering errors and log the full traceback
        logger.error(f"Error rendering admin_verification.html template: {str(e)}", exc_info=True)
        # Return a generic error page or message if rendering fails
        return "Internal Server Error during template rendering.", 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'success': True, 'message': '로그아웃 되었습니다.'})
    except Exception as e:
        logger.error(f"로그아웃 오류: {str(e)}")
        return jsonify({'success': False, 'message': '로그아웃 중 오류가 발생했습니다.'}), 500

@app.route('/api/current-user')
def get_current_user():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
            
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        try:
            # 사용자 정보 조회
            cursor.execute('''
                SELECT u.id, u.name, u.email, 
                       CASE WHEN av.id IS NOT NULL THEN 1 ELSE 0 END as is_admin
                FROM users u
                LEFT JOIN admin_verifications av ON u.id = av.user_id
                WHERE u.id = ?
            ''', (session['user_id'],))
            
            user = cursor.fetchone()
            if not user:
                return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404
                
            return jsonify({
                'success': True,
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'is_admin': bool(user[3])
            })
            
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
            return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {str(e)}")
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500

@app.route('/api/admin-verification', methods=['POST'])
def submit_admin_verification():
    conn = None
    try:
        data = request.get_json()
        if not data:
            logger.error("요청 데이터가 없습니다.")
            return jsonify({"success": False, "message": "요청 데이터가 없습니다."}), 400

        user_id = session.get("user_id")
        if not user_id:
            logger.error("로그인이 필요합니다.")
            return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

        # 필수 필드 검증
        required_fields = ["organization", "representative", "businessNumber", "officePhone", "address", "managerPhone"]
        for field in required_fields:
            if field not in data or not data[field]:
                logger.error(f"필수 필드 누락: {field}")
                return jsonify({"success": False, "message": f"{field} 필드는 필수입니다."}), 400

        # 데이터베이스 연결
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        # 데이터베이스에 저장
        cursor.execute("""
            INSERT INTO admin_verifications 
            (user_id, organization, representative, business_number, office_phone, address, manager_phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data["organization"],
            data["representative"],
            data["businessNumber"],
            data["officePhone"],
            data["address"],
            data["managerPhone"],
            "pending"
        ))
        
        conn.commit()
        logger.info("관리자 인증 정보가 성공적으로 저장되었습니다.")
        return jsonify({"success": True, "message": "관리자 인증이 신청되었습니다."})
        
    except sqlite3.Error as e:
        logger.error(f"데이터베이스 오류: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "데이터베이스 오류가 발생했습니다."}), 500
        
    except Exception as e:
        logger.error(f"서버 오류: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "서버 오류가 발생했습니다."}), 500
        
    finally:
        if conn:
            conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '요청 데이터가 없습니다.'}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': '이메일과 비밀번호를 모두 입력해주세요.'}), 400
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, password FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
                
            if user[1] == password:  # 비밀번호가 해싱되지 않은 경우
                session['user_id'] = user[0]
                return jsonify({'success': True, 'redirect': '/main'})
            else:
                return jsonify({'success': False, 'message': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
                
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
            return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"로그인 오류: {str(e)}")
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500

@app.route('/register-volunteer')
def register_volunteer_page():
    # 로그인 여부 확인 등 필요시 추가
    # if 'user_id' not in session:
    #     return redirect(url_for('login'))
    logger.debug("Rendering register_volunteer.html page.")
    return render_template('register_volunteer.html')

@app.route('/manage-volunteers')
def manage_volunteers():
    # 관리자만 접근 가능하도록 체크 (예시: 세션 또는 데코레이터 사용)
    # if not session.get('is_admin'):
    #     flash('관리자 권한이 필요합니다.', 'warning')
    #     return redirect(url_for('main_page'))
    
    conn_v = None
    applications = []
    try:
        conn_v = sqlite3.connect('volunteer.db')
        conn_v.row_factory = sqlite3.Row
        cursor_v = conn_v.cursor()
        
        # 모든 봉사 신청 내역 조회 (JOIN 없이 volunteer_applications 테이블만 사용)
        cursor_v.execute("""
            SELECT id, applicant_name, applicant_email, volunteer_date, application_date, status
            FROM volunteer_applications
            ORDER BY application_date DESC
        """)
        applications = cursor_v.fetchall()
        logger.debug(f"Fetched {len(applications)} volunteer applications.")
        
    except sqlite3.Error as e:
        logger.error(f"봉사 신청 목록 조회 중 데이터베이스 오류: {str(e)}", exc_info=True)
        flash("신청 목록을 불러오는 중 오류가 발생했습니다.", "error")
    except Exception as e:
        logger.error(f"봉사 신청 목록 조회 중 서버 오류: {str(e)}", exc_info=True)
        flash("신청 목록을 불러오는 중 오류가 발생했습니다.", "error")
    finally:
        if conn_v:
            conn_v.close()
            
    return render_template('manage_volunteers.html', applications=applications)

@app.route('/api/update-application-status', methods=['POST'])
def update_application_status():
    # 관리자 권한 체크 필요
    data = request.get_json()
    application_ids = data.get('ids')
    new_status = data.get('status') # 'approved' 또는 'rejected'

    if not application_ids or not new_status or new_status not in ['approved', 'rejected']:
        logger.warning(f"Invalid data received for status update: ids={application_ids}, status={new_status}")
        return jsonify({'success': False, 'message': '잘못된 요청입니다.'}), 400

    conn_v = None
    updated_count = 0
    try:
        conn_v = sqlite3.connect('volunteer.db')
        cursor_v = conn_v.cursor()
        
        # ID 목록을 사용하여 상태 업데이트 (SQL 인젝션 방지)
        placeholders = ','.join('?' * len(application_ids))
        sql = f"UPDATE volunteer_applications SET status = ? WHERE id IN ({placeholders}) AND status = 'pending'" # 대기 중인 신청만 변경
        
        params = [new_status] + application_ids
        cursor_v.execute(sql, params)
        updated_count = cursor_v.rowcount # 변경된 행의 수
        conn_v.commit()
        logger.info(f"Updated status to '{new_status}' for {updated_count} applications: IDs={application_ids}")
        
        return jsonify({'success': True, 'message': f'{updated_count}건의 신청 상태가 변경되었습니다.', 'updated_count': updated_count})

    except sqlite3.Error as e:
        logger.error(f"봉사 신청 상태 업데이트 중 데이터베이스 오류: {str(e)}", exc_info=True)
        if conn_v:
            conn_v.rollback()
        return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
    except Exception as e:
        logger.error(f"봉사 신청 상태 업데이트 중 서버 오류: {str(e)}", exc_info=True)
        if conn_v:
            conn_v.rollback()
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500
    finally:
        if conn_v:
            conn_v.close()
            
@app.route('/download-applications')
def download_applications():
    # 관리자 권한 체크 필요
    conn_v = None
    try:
        conn_v = sqlite3.connect('volunteer.db')
        # Pandas를 사용하여 데이터베이스 테이블 읽기
        df = pd.read_sql_query("SELECT id as 순번, applicant_name as 회원명, applicant_email as 회원ID, volunteer_date as 활동일자, application_date as 신청날짜, status as 상태 FROM volunteer_applications ORDER BY application_date DESC", conn_v)
        
        # 날짜 형식 변환 (선택 사항)
        if '신청날짜' in df.columns:
             df['신청날짜'] = pd.to_datetime(df['신청날짜']).dt.strftime('%Y-%m-%d %H:%M:%S')
             
        # BytesIO를 사용하여 메모리에서 엑셀 파일 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='봉사신청자목록')
        output.seek(0)
        
        logger.info("Generated Excel file for volunteer applications.")
        
        # 파일 다운로드 응답 생성
        return send_file(
            output, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            download_name='봉사신청자_목록.xlsx', 
            as_attachment=True
        )

    except sqlite3.Error as e:
        logger.error(f"엑셀 다운로드 중 데이터베이스 오류: {str(e)}", exc_info=True)
        flash("엑셀 파일 생성 중 오류가 발생했습니다.", "error")
        return redirect(url_for('manage_volunteers'))
    except Exception as e:
        logger.error(f"엑셀 다운로드 중 오류: {str(e)}", exc_info=True)
        flash("엑셀 파일 생성 중 오류가 발생했습니다.", "error")
        return redirect(url_for('manage_volunteers'))
    finally:
        if conn_v:
            conn_v.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 