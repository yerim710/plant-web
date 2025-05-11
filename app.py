from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, send_file, session, flash
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
# 비밀번호 해싱 함수 임포트
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
from functools import wraps
import json
import secrets # 보안 강화를 위해 secrets 모듈 사용
from collections import defaultdict

# 허용할 파일 확장자 목록
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# 파일 확장자 검사 함수
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 현재 디렉토리의 절대 경로를 구합니다
current_dir = os.path.dirname(os.path.abspath(__file__))
logger.debug(f"Current directory: {current_dir}")

# 데이터베이스 파일 경로 설정
USERS_DB_PATH = os.path.join(current_dir, 'users.db')
VOLUNTEER_DB_PATH = os.path.join(current_dir, 'volunteer.db')

# Database setup for email verification
def init_email_verification_db():
    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        # Check if table exists first to avoid errors on restart if already created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_verifications'")
        table_exists = cursor.fetchone()
        if not table_exists:
            cursor.execute("""
                CREATE TABLE email_verifications (
                    email TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()
            logger.info("Email verifications table created.")
        else:
            logger.info("Email verifications table already exists.")
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize email verifications table: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

init_email_verification_db() # Call this at startup

app = Flask(__name__, static_folder='static')
CORS(app)

# 파일 업로드 폴더 설정 추가
UPLOAD_FOLDER = os.path.join(current_dir, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = 'your-secret-key'  # 세션을 위한 비밀 키

# 로그인 확인 데코레이터 추가
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # 로그인 페이지로 리디렉션, 원래 요청했던 URL을 next 파라미터로 전달
            return redirect(url_for('login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 관리자 확인 데코레이터
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('login_page', next=request.url))
        
        user_id = session['user_id']
        current_user = get_user_from_session() # 사용자 정보 가져오기

        is_authorized_admin = False
        if current_user and current_user.get('email') == 'admin@test.com':
            is_authorized_admin = True # admin@test.com은 항상 관리자로 간주
            logger.info(f"[@admin_required] User admin@test.com (ID: {user_id}) authorized as admin by email.")
        elif current_user and current_user.get('is_admin'): # get_user_from_session의 is_admin 결과 활용
            is_authorized_admin = True
            logger.info(f"[@admin_required] User ID {user_id} authorized as admin based on current_user.is_admin flag.")
        # else: # is_authorized_admin이 False로 유지됨
            # logger.warning(f"[@admin_required] Admin access denied for user_id: {user_id} if not caught by above.")
            
        if not is_authorized_admin:
            logger.warning(f"[@admin_required] Admin access DENIED for user_id: {user_id}. Redirecting to admin_verification.")
            flash('이 기능을 사용하려면 관리자 인증이 필요합니다. 먼저 인증 신청을 완료해주세요.', 'warning') 
            return redirect(url_for('admin_verification')) 
            
        logger.debug(f"[@admin_required] Admin access GRANTED for user_id: {user_id}")
        return f(*args, **kwargs)
    return decorated_function

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
        return render_template('login.html')
    except Exception as e:
        logger.error(f"홈 페이지 로드 오류: {str(e)}")
        try:
            return render_template('login.html')
        except:
            return "An error occurred loading the home page.", 500

@app.route('/login')
def login_page():
    try:
        if 'user_id' in session:
            return redirect(url_for('main_page'))
        return render_template('login.html')
    except Exception as e:
        logger.error(f"로그인 페이지 로드 오류: {str(e)}")
        try:
            return render_template('login.html')
        except:
            return "An error occurred loading the login page.", 500

@app.route('/signup')
def signup_page():
    try:
        return render_template('signup.html')
    except Exception as e:
        logger.error(f"회원가입 페이지 로드 오류: {str(e)}")
        try:
            return render_template('signup.html')
        except:
            return "An error occurred loading the signup page.", 500

# Function to get current user info (avoids repetition)
def get_user_from_session():
    user_id = session.get('user_id')
    if not user_id:
        logger.debug("get_user_from_session: No user_id in session.")
        return None
    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # 기본 사용자 정보 조회 (id, name, email)
        cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            logger.warning(f"get_user_from_session: User info not found in DB for ID {user_id}")
            return None

        user_info = dict(user_data) # Row 객체를 dict로 변환하여 수정 가능하게 함

        # admin@test.com 사용자는 항상 관리자로 간주
        if user_info['email'] == 'admin@test.com':
            user_info['is_admin'] = True
            logger.info(f"get_user_from_session: User admin@test.com (ID: {user_id}) is explicitly treated as admin.")
        else:
            # 다른 사용자들은 DB의 admin_verifications 테이블 확인
            cursor.execute("""
                SELECT CASE WHEN EXISTS (SELECT 1 FROM admin_verifications av WHERE av.user_id = ? AND av.status = 'approved') THEN 1 ELSE 0 END as is_admin_flag
            """, (user_id,))
            admin_status_result = cursor.fetchone()
            user_info['is_admin'] = bool(admin_status_result['is_admin_flag']) if admin_status_result else False
            logger.debug(f"get_user_from_session: User ID {user_id}, DB admin_status: {user_info['is_admin']}")

        # 최종 user_info 객체 (id, name, email, is_admin 포함) 로깅 및 반환
        logger.debug(f"get_user_from_session: Returning user info for ID {user_id}: Name={user_info.get('name')}, Email={user_info.get('email')}, IsAdmin={user_info.get('is_admin')}")
        return user_info # dict 반환
    except sqlite3.Error as e:
        logger.error(f"get_user_from_session: DB Error fetching user info for ID {user_id}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"get_user_from_session: General Error fetching user info for ID {user_id}: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

@app.route('/main')
@login_required
def main_page():
    current_user = get_user_from_session() 
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page'))
    return render_template('main.html', current_user=current_user, page_type='main')

@app.route('/register-volunteer')
@login_required
def register_volunteer_page():
    current_user = get_user_from_session() 
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page')) 
    return render_template('register_volunteer.html', current_user=current_user, page_type='register_volunteer')

@app.route('/manage-volunteers')
@login_required
def manage_volunteers_page():
    current_user = get_user_from_session() 
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page'))
        
    conn_v = None
    applications = []
    try:
        conn_v = sqlite3.connect(VOLUNTEER_DB_PATH)
        conn_v.row_factory = sqlite3.Row
        cursor_v = conn_v.cursor()
        cursor_v.execute("""SELECT 
                           va.id, 
                           va.applicant_name, 
                           va.applicant_email, 
                           v.activity_title, 
                           va.volunteer_date, 
                           v.activity_time_start, 
                           v.activity_time_end, 
                           v.credited_hours,
                           va.application_date, 
                           va.status 
                       FROM volunteer_applications va 
                       JOIN volunteers v ON va.volunteer_id = v.id 
                       ORDER BY va.application_date DESC""")
        applications = cursor_v.fetchall()
    except sqlite3.Error as e:
        logger.error(f"봉사 신청 목록 조회 중 데이터베이스 오류: {str(e)}", exc_info=True)
        flash("신청 목록을 불러오는 중 오류가 발생했습니다.", "error")
    except Exception as e:
        logger.error(f"봉사 신청 목록 조회 중 서버 오류: {str(e)}", exc_info=True)
        flash("신청 목록을 불러오는 중 오류가 발생했습니다.", "error")
    finally:
        if conn_v:
            conn_v.close()
            
    return render_template('manage_volunteers.html', applications=applications, current_user=current_user, page_type='manage_volunteers')

@app.route('/profile')
@login_required
def profile_page():
    current_user = get_user_from_session() 
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page'))
    return render_template('profile.html', current_user=current_user, page_type='profile')

@app.route('/admin-verification')
@login_required 
def admin_verification():
    current_user = get_user_from_session() 
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page'))

    conn = None
    verification = None
    try:
        logger.debug(f"Fetching admin verification status for user_id: {current_user['id']}")
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, organization, status, created_at, rejection_reason FROM admin_verifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (current_user['id'],))
        verification = cursor.fetchone()
        if verification:
             logger.debug(f"Found verification record for user {current_user['id']}: ID={verification['id']}, Status={verification['status']}")
        else:
             logger.debug(f"No verification record found for user {current_user['id']}.")

    except sqlite3.Error as e:
        logger.error(f"Database error fetching verification data for user {current_user['id']}: {str(e)}", exc_info=True)
        verification = None 
    except Exception as e:
        logger.error(f"Server error fetching verification data for user {current_user['id']}: {str(e)}", exc_info=True)
        verification = None 
    finally:
        if conn:
            conn.close()
            
    return render_template('admin_verification.html', verification=verification, current_user=current_user, user=current_user, page_type='admin_verification')

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
    user_id = session.get('user_id') # 함수 시작 부분에서 ID 가져오기
    logger.debug(f"[/api/current-user] Request received for user_id: {user_id}") # 로그 추가
    try:
        if not user_id:
            logger.warning("[/api/current-user] No user_id in session.")
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
            
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT u.id, u.name, u.email, 
                       CASE 
                           WHEN EXISTS (
                               SELECT 1 FROM admin_verifications av 
                               WHERE av.user_id = u.id AND av.status = 'approved'
                           ) THEN 1 
                           ELSE 0 
                       END as is_admin_flag
                FROM users u
                WHERE u.id = ?
            ''', (user_id,))
            
            user = cursor.fetchone()
            if not user:
                # ... (사용자 없음 처리, 로그 추가 가능)
                logger.warning(f"[/api/current-user] User ID {user_id} not found in DB.")
                return jsonify({'success': False, 'message': '사용자 정보를 찾을 수 없습니다. 다시 로그인해주세요.'}), 404
                
            # is_admin 값 로깅 추가
            is_admin_result = bool(user[3])
            logger.debug(f"[/api/current-user] Fetched user info for user_id {user_id}. is_admin determined as: {is_admin_result}")
            
            return jsonify({
                'success': True,
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'is_admin': is_admin_result 
            })
            
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
            return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
            
        finally:
            if conn:
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
        conn = sqlite3.connect(USERS_DB_PATH)
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
        
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, password FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
                
            user_id = user[0]
            hashed_password_from_db = user[1]
            
            # 사용자가 입력한 비밀번호와 DB에 저장된 해시된 비밀번호를 비교
            if check_password_hash(hashed_password_from_db, password):
                # 비밀번호 일치: 로그인 성공
                session['user_id'] = user_id
                logger.info(f"User {email} (ID: {user_id}) logged in successfully.")
                return jsonify({'success': True, 'redirect': '/main'})
            else:
                # 비밀번호 불일치
                logger.warning(f"Login failed for user {email}: Incorrect password.")
                return jsonify({'success': False, 'message': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
                
        except sqlite3.Error as e:
            logger.error(f"데이터베이스 오류: {str(e)}")
            return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"로그인 오류: {str(e)}")
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500

@app.route('/api/update-application-status', methods=['POST'])
@login_required # 관리자 권한은 필요 시 추가
def update_application_status():
    data = request.get_json()
    application_ids = data.get('ids')
    new_status = data.get('status') # 'approved' 또는 'rejected'
    rejection_reason = data.get('reason') # 반려 사유 추가

    if not application_ids or not new_status or new_status not in ['approved', 'rejected']:
        logger.warning(f"Invalid data received for status update: ids={application_ids}, status={new_status}")
        return jsonify({'success': False, 'message': '잘못된 요청입니다.'}), 400

    # 반려 시 사유 필수 확인 (선택적)
    if new_status == 'rejected' and not rejection_reason:
        return jsonify({'success': False, 'message': '반려 사유를 입력해야 합니다.'}), 400

    conn_v = None
    updated_count = 0
    try:
        conn_v = sqlite3.connect(VOLUNTEER_DB_PATH)
        cursor_v = conn_v.cursor()
        
        placeholders = ','.join('?' * len(application_ids))
        
        # 상태 및 반려 사유 업데이트 SQL
        sql = f"""
            UPDATE volunteer_applications 
            SET status = ?,
                rejection_reason = CASE WHEN ? = 'rejected' THEN ? ELSE NULL END 
            WHERE id IN ({placeholders}) AND status = 'pending'
        """
        # 반려 상태일 때만 reason을 업데이트하고, 승인 시에는 NULL로 초기화
        
        params = [new_status, new_status, rejection_reason] + application_ids # 파라미터 순서 주의
        
        cursor_v.execute(sql, params)
        updated_count = cursor_v.rowcount
        conn_v.commit()
        logger.info(f"Updated status to '{new_status}' for {updated_count} applications: IDs={application_ids}. Reason: {rejection_reason if new_status == 'rejected' else 'N/A'}")
        
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
        conn_v = sqlite3.connect(VOLUNTEER_DB_PATH)
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

@app.route('/api/volunteers', methods=['GET'])
def get_volunteers():
    conn = None
    try:
        conn = sqlite3.connect(VOLUNTEER_DB_PATH)
        conn.row_factory = sqlite3.Row # Ensure rows can be accessed like dicts
        c = conn.cursor()

        # Base query with all necessary columns, including aliased image_path
        base_query = '''
            SELECT 
                id, user_id, activity_title, volunteer_content, activity_type, 
                activity_period_start, activity_period_end, activity_time_start, 
                activity_time_end, activity_days, address, address_detail, 
                volunteer_type, manager_name, manager_phone, manager_email, 
                max_volunteers, current_volunteers, credited_hours, created_at,
                attachment_path AS image_path
            FROM volunteers
        '''
        
        # Sorting parameters
        sort_by = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        
        allowed_sort_columns = ['created_at', 'activity_period_start', 'max_volunteers']
        allowed_orders = ['asc', 'desc']

        # Build the ORDER BY clause safely
        order_clause = ""
        if sort_by in allowed_sort_columns and order in allowed_orders:
            order_clause = f" ORDER BY {sort_by} {order}"
        # elif sort_by == 'duration': # Example for duration if needed later
            # order_clause = f" ORDER BY date(activity_period_start) {order if order in allowed_orders else 'asc'}"
        else:
            # Default sort
            order_clause = " ORDER BY created_at DESC"

        # Combine base query and order clause
        query = base_query + order_clause
        
        logger.debug(f"Executing query: {query}")
        c.execute(query)
        volunteers_raw = c.fetchall()
        
        # Get column names from cursor description *after* execution
        column_names = [description[0] for description in c.description]
        conn.close() # Close connection after fetching
        conn = None # Reset conn variable

        # Convert results to list of dictionaries
        volunteers = [dict(zip(column_names, row)) for row in volunteers_raw]
        logger.debug(f"Fetched volunteers: {volunteers}")

        return jsonify({'success': True, 'volunteers': volunteers})

    except sqlite3.Error as db_err:
        logger.error(f"Database error fetching volunteers: {db_err}", exc_info=True)
        return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
    except Exception as e:
        logger.error(f"Error fetching volunteers: {e}", exc_info=True)
        return jsonify({'success': False, 'message': '봉사활동 목록을 불러오는 중 오류가 발생했습니다.'}), 500
    finally:
        if conn: # Ensure connection is closed even if error occurs before explicit close
            conn.close()
            logger.debug("Database connection closed in finally block.")

@app.route('/admin/approve-requests')
@login_required 
@admin_required 
def approve_requests_page():
    current_user = get_user_from_session() 
    if not current_user or not current_user.get('is_admin'): # Check if is_admin is true
        flash("이 페이지에 접근할 권한이 없습니다.", "warning")
        return redirect(url_for('main_page'))
        
    conn = None
    pending_requests = []
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(""" 
            SELECT av.id, u.name as user_name, u.email as user_email, 
                   av.organization, av.representative, av.business_number, 
                   av.office_phone, av.address, av.manager_phone, av.created_at
            FROM admin_verifications av
            JOIN users u ON av.user_id = u.id
            WHERE av.status = 'pending'
            ORDER BY av.created_at ASC
        """)
        pending_requests = cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Pending admin requests 조회 중 DB 오류: {str(e)}", exc_info=True)
        flash("신청 목록 조회 중 오류가 발생했습니다.", "error")
    except Exception as e:
        logger.error(f"Pending admin requests 조회 중 서버 오류: {str(e)}", exc_info=True)
        flash("신청 목록 조회 중 오류가 발생했습니다.", "error")
    finally:
        if conn:
            conn.close()

    return render_template('approve_requests.html', 
                           pending_requests=pending_requests, 
                           current_user=current_user, 
                           page_type='approve_requests') 

@app.route('/api/admin/approve/<int:request_id>', methods=['POST'])
@admin_required
def approve_admin_request(request_id):
    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        # 해당 ID의 신청 상태를 'approved'로 변경 (원래 'pending'이었는지 확인)
        cursor.execute("""
            UPDATE admin_verifications 
            SET status = 'approved', rejection_reason = NULL 
            WHERE id = ? AND status = 'pending'
        """, (request_id,))
        
        updated_count = cursor.rowcount # 실제로 변경된 행 수 확인
        conn.commit()
        
        if updated_count > 0:
            logger.info(f"Admin request ID {request_id} approved by user {session.get('user_id')}")
            return jsonify({'success': True, 'message': '신청이 승인되었습니다.'})
        else:
            logger.warning(f"Approval attempt failed for already processed or non-existent request ID {request_id}")
            # 이미 처리되었거나 존재하지 않는 ID일 수 있음
            return jsonify({'success': False, 'message': '이미 처리되었거나 유효하지 않은 신청입니다.'}), 404
            
    except sqlite3.Error as e:
        logger.error(f"DB 오류 - Admin request approval ID {request_id}: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '데이터베이스 오류 발생'}), 500
    except Exception as e:
        logger.error(f"서버 오류 - Admin request approval ID {request_id}: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '서버 오류 발생'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/reject/<int:request_id>', methods=['POST'])
@admin_required
def reject_admin_request(request_id):
    conn = None
    try:
        data = request.get_json()
        rejection_reason = data.get('reason')
        if not rejection_reason:
            return jsonify({'success': False, 'message': '반려 사유를 입력해야 합니다.'}), 400
            
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        # 해당 ID의 신청 상태를 'rejected'로 변경하고 사유 저장 (원래 'pending'이었는지 확인)
        cursor.execute("""
            UPDATE admin_verifications 
            SET status = 'rejected', rejection_reason = ? 
            WHERE id = ? AND status = 'pending'
        """, (rejection_reason, request_id))
        
        updated_count = cursor.rowcount
        conn.commit()
        
        if updated_count > 0:
            logger.info(f"Admin request ID {request_id} rejected by user {session.get('user_id')} with reason: {rejection_reason}")
            return jsonify({'success': True, 'message': '신청이 반려되었습니다.'})
        else:
            logger.warning(f"Rejection attempt failed for already processed or non-existent request ID {request_id}")
            return jsonify({'success': False, 'message': '이미 처리되었거나 유효하지 않은 신청입니다.'}), 404
            
    except sqlite3.Error as e:
        logger.error(f"DB 오류 - Admin request rejection ID {request_id}: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '데이터베이스 오류 발생'}), 500
    except Exception as e:
        logger.error(f"서버 오류 - Admin request rejection ID {request_id}: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '서버 오류 발생'}), 500
    finally:
        if conn:
            conn.close()

# 사용자 이름 변경 API
@app.route('/api/change-name', methods=['POST'])
@login_required
def change_name():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json()
    new_name = data.get('newName')

    if not new_name or not new_name.strip():
        return jsonify({'success': False, 'message': '새 이름을 입력해주세요.'}), 400
    
    new_name = new_name.strip() # 앞뒤 공백 제거

    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, user_id))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"User {user_id}'s name changed successfully to '{new_name}'")
            return jsonify({'success': True, 'message': '이름이 성공적으로 변경되었습니다.'})
        else:
            # 이 경우는 거의 없지만, user_id가 DB에 없는 경우 발생 가능
            logger.warning(f"Failed to change name for non-existent user_id: {user_id}")
            return jsonify({'success': False, 'message': '사용자 정보를 찾을 수 없습니다.'}), 404

    except sqlite3.Error as e:
        logger.error(f"Database error changing name for user {user_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
    except Exception as e:
        logger.error(f"Server error changing name for user {user_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500
    finally:
        if conn:
            conn.close()

# 사용자 이메일 변경 API
@app.route('/api/change-email', methods=['POST'])
@login_required
def change_email():
    # TODO: 이메일 변경 로직 구현 필요
    # 1. 새 이메일 주소 받기
    # 2. (선택) 현재 비밀번호 확인
    # 3. (선택) 새 이메일 주소 유효성 검사 (예: 형식, 중복 여부)
    # 4. (선택) 새 이메일 주소로 인증 코드 발송 및 확인 절차 추가
    # 5. DB의 이메일 주소 업데이트
    # 6. 성공/실패 메시지 반환
    logger.warning("/api/change-email endpoint is called but not implemented yet.")
    return jsonify({'success': False, 'message': '이메일 변경 기능은 아직 구현되지 않았습니다.'}), 501 # 501 Not Implemented

# 회원 탈퇴 API
@app.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    conn_users = None
    try:
        # 사용자 DB 연결
        conn_users = sqlite3.connect(USERS_DB_PATH)
        cursor_users = conn_users.cursor()

        # 봉사 DB 연결 (관련 데이터 삭제용)
        conn_volunteer = sqlite3.connect(VOLUNTEER_DB_PATH)
        cursor_volunteer = conn_volunteer.cursor()

        # 1. 관련 데이터 삭제 (admin_verifications)
        cursor_users.execute("DELETE FROM admin_verifications WHERE user_id = ?", (user_id,))
        logger.info(f"Deleted admin_verifications for user_id: {user_id}")

        # 2. 관련 데이터 삭제 (volunteer_applications)
        cursor_volunteer.execute("DELETE FROM volunteer_applications WHERE user_id = ?", (user_id,))
        logger.info(f"Deleted volunteer_applications for user_id: {user_id}")

        # TODO: 사용자가 등록한 봉사활동(volunteers 테이블)도 삭제할지 정책 결정 필요
        # cursor_volunteer.execute("DELETE FROM volunteers WHERE user_id = ?", (user_id,)) 

        # 3. 사용자 계정 삭제 (users)
        cursor_users.execute("DELETE FROM users WHERE id = ?", (user_id,))
        logger.info(f"Deleted user account for user_id: {user_id}")

        # 변경사항 커밋
        conn_users.commit()
        conn_volunteer.commit()

        # 세션 클리어 (로그아웃 처리)
        session.clear()

        return jsonify({'success': True, 'message': '회원 탈퇴가 완료되었습니다.'})

    except sqlite3.Error as e:
        logger.error(f"Database error during account deletion for user {user_id}: {e}", exc_info=True)
        if conn_users:
            conn_users.rollback()
        if conn_volunteer:
            conn_volunteer.rollback()
        return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
    except Exception as e:
        logger.error(f"Server error during account deletion for user {user_id}: {e}", exc_info=True)
        if conn_users:
            conn_users.rollback()
        if conn_volunteer:
            conn_volunteer.rollback()
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500
    finally:
        if conn_users:
            conn_users.close()
        if conn_volunteer:
            conn_volunteer.close()

# 관리자 인증 신청 목록 엑셀 다운로드
@app.route('/admin/download-requests')
@admin_required
def download_admin_requests():
    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # status가 'pending'인 신청 내역 조회 (users 테이블과 JOIN하여 이름, 이메일 포함)
        cursor.execute(""" 
            SELECT 
                av.id as 신청ID, 
                u.name as 신청자명, 
                u.email as 신청자이메일, 
                av.organization as 기관명, 
                av.representative as 대표자명, 
                av.business_number as 사업자번호, 
                av.office_phone as 사무실전화, 
                av.address as 주소, 
                av.manager_phone as 담당자연락처, 
                av.created_at as 신청일
            FROM admin_verifications av
            JOIN users u ON av.user_id = u.id
            WHERE av.status = 'pending'
            ORDER BY av.created_at ASC
        """)
        pending_requests = cursor.fetchall()

        if not pending_requests:
            flash("다운로드할 대기 중인 신청 내역이 없습니다.", "info")
            return redirect(url_for('approve_requests_page'))

        # Pandas DataFrame 생성
        df = pd.DataFrame([dict(row) for row in pending_requests])

        # 날짜 형식 변환 (선택 사항)
        if '신청일' in df.columns:
             df['신청일'] = pd.to_datetime(df['신청일']).dt.strftime('%Y-%m-%d %H:%M:%S')
             
        # BytesIO를 사용하여 메모리에서 엑셀 파일 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='관리자인증신청_대기')
        output.seek(0)
        
        logger.info("Generated Excel file for pending admin verification requests.")
        
        # 파일 다운로드 응답 생성
        return send_file(
            output, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            download_name='관리자인증신청_대기목록.xlsx', 
            as_attachment=True
        )

    except sqlite3.Error as e:
        logger.error(f"엑셀 다운로드 중 데이터베이스 오류 (Admin Requests): {str(e)}", exc_info=True)
        flash("엑셀 파일 생성 중 오류가 발생했습니다.", "error")
        return redirect(url_for('approve_requests_page'))
    except Exception as e:
        logger.error(f"엑셀 다운로드 중 오류 (Admin Requests): {str(e)}", exc_info=True)
        flash("엑셀 파일 생성 중 오류가 발생했습니다.", "error")
        return redirect(url_for('approve_requests_page'))
    finally:
        if conn:
            conn.close()

# 봉사활동 등록 API
@app.route('/api/register-volunteer', methods=['POST'])
@login_required
@admin_required # 관리자만 등록 가능하도록 설정
def register_volunteer_activity():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    # FormData 처리
    if not request.form:
         return jsonify({'success': False, 'message': '폼 데이터가 없습니다.'}), 400

    logger.debug(f"Received form data: {request.form}")
    logger.debug(f"Received files: {request.files}")

    # 필수 필드 확인 (HTML에서 required 했더라도 서버에서 한번 더 확인)
    # registration_org, admin_memo 등 제거된 필드는 제외
    required_fields = [
        'activity_title', 'volunteer_content', 'activity_type', 'activity_period_start',
        'activity_period_end', 'activity_time_start', 'activity_time_end',
        'volunteer_type', 'manager_name', 'manager_phone', 'manager_email',
        'max_volunteers', 'credited_hours'
    ]
    # address, address_detail 은 카카오 API 결과가 없을 수도 있으므로 필수에서 제외 (선택적 처리)

    missing_fields = [field for field in required_fields if field not in request.form or not request.form[field]]
    if missing_fields:
        return jsonify({'success': False, 'message': f'필수 항목 누락: {", ".join(missing_fields)}'}), 400

    # 활동 요일 처리
    activity_days_list = request.form.getlist('activity_days') # 체크박스는 getlist 사용
    activity_days_db_format = ','.join(activity_days_list) if activity_days_list else None

    # 파일 처리 (이전 예시 코드 참조)
    attachment_path = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename != '':
            if allowed_file(file.filename):
                # 새 파일 저장
                filename = secure_filename(file.filename)
                base, extension = os.path.splitext(filename)
                timestamp = int(time.time())
                unique_filename = f"{base}_{timestamp}{extension}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                
                try:
                    file.save(upload_path)
                    attachment_path = os.path.join('uploads', unique_filename).replace('\\', '/')
                    logger.info(f"New file uploaded for volunteer {user_id}: {attachment_path}")
                except Exception as e:
                     logger.error(f"File upload failed during update for volunteer {user_id}: {e}", exc_info=True)
                     return jsonify({'success': False, 'message': '파일 업로드 중 오류 발생'}), 500
            else:
                return jsonify({'success': False, 'message': '허용되지 않는 파일 형식입니다.'}), 400
    
    # 데이터베이스 저장
    conn = None
    try:
        conn = sqlite3.connect(VOLUNTEER_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO volunteers (
                user_id, activity_title, volunteer_content, activity_type, activity_period_start,
                activity_period_end, activity_time_start, activity_time_end, activity_days,
                attachment_path, address, address_detail, volunteer_type, manager_name,
                manager_phone, manager_email, max_volunteers, credited_hours, created_at
                -- latitude, longitude는 지도 구현 후 추가
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            request.form['activity_title'],
            request.form['volunteer_content'],
            request.form['activity_type'],
            request.form['activity_period_start'],
            request.form['activity_period_end'],
            request.form['activity_time_start'],
            request.form['activity_time_end'],
            activity_days_db_format,
            attachment_path,
            request.form.get('address'), # 주소 필드
            request.form.get('address_detail'), # 상세 주소 필드
            request.form['volunteer_type'],
            request.form['manager_name'],
            request.form['manager_phone'],
            request.form['manager_email'],
            int(request.form['max_volunteers']), # 숫자형으로 변환
            request.form['credited_hours'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        logger.info(f"Volunteer activity registered successfully by admin user_id: {user_id}")
        return jsonify({'success': True, 'message': '봉사 활동이 성공적으로 등록되었습니다.'})

    except sqlite3.Error as e:
        logger.error(f"Database error during volunteer registration: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'데이터베이스 오류 발생: {e}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error during volunteer registration: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'서버 오류 발생: {e}'}), 500
    finally:
        if conn:
            conn.close()

# 봉사활동 삭제 API
@app.route('/api/volunteer/delete/<int:volunteer_id>', methods=['DELETE'])
@login_required
@admin_required # 관리자만 삭제 가능
def delete_volunteer_activity(volunteer_id):
    user_id = session.get('user_id')
    conn = None
    try:
        conn = sqlite3.connect(VOLUNTEER_DB_PATH)
        cursor = conn.cursor()

        # 0. 해당 봉사활동이 현재 관리자가 등록한 것인지 확인 (선택적 강화)
        # cursor.execute("SELECT user_id FROM volunteers WHERE id = ?", (volunteer_id,))
        # owner = cursor.fetchone()
        # if not owner or owner[0] != user_id:
        #     logger.warning(f"User {user_id} attempted to delete volunteer {volunteer_id} owned by {owner[0] if owner else 'unknown'}")
        #     # 권한 없음 또는 찾을 수 없음 오류 반환 (403 또는 404)
        #     return jsonify({'success': False, 'message': '삭제 권한이 없거나 해당 활동을 찾을 수 없습니다.'}), 403 

        # 1. 해당 봉사활동에 대한 신청 내역 삭제 (volunteer_applications)
        cursor.execute("DELETE FROM volunteer_applications WHERE volunteer_id = ?", (volunteer_id,))
        deleted_applications_count = cursor.rowcount
        logger.info(f"Deleted {deleted_applications_count} applications for volunteer ID: {volunteer_id}")

        # 2. 봉사활동 자체 삭제 (volunteers)
        cursor.execute("DELETE FROM volunteers WHERE id = ?", (volunteer_id,))
        deleted_volunteer_count = cursor.rowcount

        if deleted_volunteer_count > 0:
            conn.commit()
            logger.info(f"Volunteer activity ID {volunteer_id} deleted successfully by admin user_id: {user_id}")
            return jsonify({'success': True, 'message': '봉사 활동이 성공적으로 삭제되었습니다.'})
        else:
            # 삭제할 봉사활동이 없는 경우 (이미 삭제되었거나 ID가 잘못된 경우)
            logger.warning(f"Attempted to delete non-existent volunteer activity ID: {volunteer_id}")
            conn.rollback() # 롤백 (신청내역 삭제도 취소)
            return jsonify({'success': False, 'message': '삭제할 봉사 활동을 찾을 수 없습니다.'}), 404

    except sqlite3.Error as e:
        logger.error(f"Database error deleting volunteer activity {volunteer_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'데이터베이스 오류 발생: {e}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error deleting volunteer activity {volunteer_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'서버 오류 발생: {e}'}), 500
    finally:
        if conn:
            conn.close()

# 봉사활동 수정 페이지 라우트
@app.route('/edit-volunteer/<int:volunteer_id>')
@login_required
@admin_required
def edit_volunteer_page(volunteer_id):
    conn = None
    volunteer_data = None
    current_user = get_user_from_session() # Get current user
    try:
        conn = sqlite3.connect(VOLUNTEER_DB_PATH)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,))
        volunteer_data = cursor.fetchone()

        if not volunteer_data:
            flash('수정할 봉사 활동 정보를 찾을 수 없습니다.', 'error')
            return redirect(url_for('main_page')) 

        return render_template('edit_volunteer.html', volunteer=volunteer_data, current_user=current_user, page_type='manage_volunteers') # Pass current_user and page_type (e.g. 'manage_volunteers' to highlight parent)

    except sqlite3.Error as e:
        logger.error(f"Database error fetching volunteer {volunteer_id} for edit: {e}", exc_info=True)
        flash('봉사 활동 정보를 불러오는 중 오류가 발생했습니다.', 'error')
        return redirect(url_for('main_page'))
    except Exception as e:
        logger.error(f"Server error fetching volunteer {volunteer_id} for edit: {e}", exc_info=True)
        flash('서버 오류가 발생했습니다.', 'error')
        return redirect(url_for('main_page'))
    finally:
        if conn:
            conn.close()

# 봉사활동 수정 내용 저장 API
@app.route('/api/volunteer/update/<int:volunteer_id>', methods=['POST'])
@login_required
@admin_required
def update_volunteer_activity(volunteer_id):
    user_id = session.get('user_id')
    conn = None
    try:
        if not request.form:
            return jsonify({'success': False, 'message': '폼 데이터가 없습니다.'}), 400

        logger.debug(f"Received form data for update (ID: {volunteer_id}): {request.form}")
        logger.debug(f"Received files for update (ID: {volunteer_id}): {request.files}")

        conn = sqlite3.connect(VOLUNTEER_DB_PATH)
        cursor = conn.cursor()

        # 기존 첨부 파일 경로 조회 (삭제 처리를 위해)
        cursor.execute("SELECT attachment_path FROM volunteers WHERE id = ?", (volunteer_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'success': False, 'message': '수정할 봉사 활동을 찾을 수 없습니다.'}), 404
        existing_attachment_path = result[0]
        new_attachment_path = existing_attachment_path # 기본값은 기존 경로 유지

        # 새 파일 업로드 처리
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # 새 파일 저장
                    filename = secure_filename(file.filename)
                    base, extension = os.path.splitext(filename)
                    timestamp = int(time.time())
                    unique_filename = f"{base}_{timestamp}{extension}"
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):
                        os.makedirs(app.config['UPLOAD_FOLDER'])
                    
                    try:
                        file.save(upload_path)
                        new_attachment_path = os.path.join('uploads', unique_filename).replace('\\', '/') # DB 저장용 경로
                        logger.info(f"New file uploaded for volunteer {volunteer_id}: {new_attachment_path}")

                        # 기존 파일 삭제 (새 파일 저장 성공 시)
                        if existing_attachment_path:
                            existing_file_full_path = os.path.join(app.root_path, 'static', existing_attachment_path)
                            if os.path.exists(existing_file_full_path):
                                try:
                                    os.remove(existing_file_full_path)
                                    logger.info(f"Old file deleted: {existing_file_full_path}")
                                except OSError as e:
                                    logger.error(f"Error deleting old file {existing_file_full_path}: {e}")
                                    # 파일 삭제 실패가 전체 프로세스를 중단시키지는 않음
                    except Exception as e:
                        logger.error(f"File upload failed during update for volunteer {volunteer_id}: {e}", exc_info=True)
                        # 파일 저장 실패 시 롤백하고 오류 반환하는 것이 좋을 수 있음
                        conn.rollback()
                        return jsonify({'success': False, 'message': '파일 업로드 중 오류 발생'}), 500
                else:
                    return jsonify({'success': False, 'message': '허용되지 않는 파일 형식입니다.'}), 400
        
        # 활동 요일 처리 (등록과 동일)
        activity_days_list = request.form.getlist('activity_days')
        activity_days_db_format = ','.join(activity_days_list) if activity_days_list else None

        # 데이터베이스 업데이트
        cursor.execute("""
            UPDATE volunteers SET
                activity_title = ?,
                volunteer_content = ?,
                activity_type = ?,
                activity_period_start = ?,
                activity_period_end = ?,
                activity_time_start = ?,
                activity_time_end = ?,
                activity_days = ?,
                attachment_path = ?, 
                address = ?,
                address_detail = ?,
                manager_name = ?,
                manager_phone = ?,
                manager_email = ?,
                max_volunteers = ?,
                credited_hours = ?
            WHERE id = ?
        """, (
            request.form['activity_title'],
            request.form['volunteer_content'],
            request.form['activity_type'],
            request.form['activity_period_start'],
            request.form['activity_period_end'],
            request.form['activity_time_start'],
            request.form['activity_time_end'],
            activity_days_db_format,
            new_attachment_path, 
            request.form.get('address'),
            request.form.get('address_detail'),
            request.form['manager_name'],
            request.form['manager_phone'],
            request.form['manager_email'],
            int(request.form['max_volunteers']), 
            request.form['credited_hours'],
            volunteer_id 
        ))

        conn.commit()
        logger.info(f"Volunteer activity ID {volunteer_id} updated successfully by admin user_id: {user_id}")
        return jsonify({'success': True, 'message': '봉사 활동 정보가 성공적으로 수정되었습니다.'})

    except sqlite3.Error as e:
        logger.error(f"Database error updating volunteer {volunteer_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'데이터베이스 오류 발생: {e}'}), 500
    except Exception as e:
        logger.error(f"Unexpected error updating volunteer {volunteer_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': f'서버 오류 발생: {e}'}), 500
    finally:
        if conn:
            conn.close()

# 임시 비밀번호 생성 함수
def generate_temp_password(length=8):
    # 영문 대소문자, 숫자, 특수문자 포함
    # 주의: 일부 특수문자는 이메일 또는 시스템에서 문제를 일으킬 수 있으므로 제한적으로 사용하거나 이스케이프 처리 필요
    # 여기서는 비교적 안전한 특수문자 일부만 사용
    characters = string.ascii_letters + string.digits + '!@#$%^&*_-'
    while True:
        password = ''.join(secrets.choice(characters) for i in range(length))
        # 최소 1개 이상의 숫자와 특수문자를 포함하는지 간단히 확인 (더 엄격한 규칙 적용 가능)
        if (any(c.isdigit() for c in password)
                and any(c in '!@#$%^&*_-' for c in password)):
            return password

# 이메일 발송 헬퍼 함수
def send_email(recipient_email, subject, body):
    # !!! IMPORTANT: Ensure SMTP settings are correctly configured below !!!
    # Consider using environment variables or a config file for security
    smtp_server = "smtp.naver.com" # 네이버 SMTP 서버 주소
    smtp_port = 587 # TLS 용 일반 포트
    smtp_user = "yerim8896@naver.com" # 실제 네이버 이메일 주소
    smtp_password = "4NQY982C9K12" # 실제 네이버 앱 비밀번호 (또는 계정 비밀번호)
    sender_email = "yerim8896@naver.com" # 실제 발신자 이메일 주소

    msg = MIMEText(body, _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        # 네이버 + starttls (port 587) 사용
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        logger.info(f"Email successfully sent to {recipient_email} with subject: {subject}")
        return True # 성공 시 True 반환
    except smtplib.SMTPAuthenticationError:
        logger.error(f"SMTP Authentication failed for user {smtp_user}. Check credentials.")
        return False # 실패 시 False 반환
    except smtplib.SMTPServerDisconnected:
         logger.error("SMTP server disconnected unexpectedly.")
         return False
    except smtplib.SMTPRecipientsRefused:
         logger.error(f"Recipient address {recipient_email} refused by the server.")
         return False
    except smtplib.SMTPException as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}", exc_info=True)
        return False
    except Exception as e:
         logger.error(f"An unexpected error occurred during email sending to {recipient_email}: {e}", exc_info=True)
         return False

# 비밀번호 재설정 요청 처리 API
@app.route('/api/reset-password-request', methods=['POST'])
def reset_password_request():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'message': '이메일을 입력해주세요.'}), 400

    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        # 사용자 존재 확인
        cursor.execute("SELECT id, name FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            user_id, user_name = user
            # 임시 비밀번호 생성
            temp_password = generate_temp_password()
            logger.info(f"Generated temporary password for user {email} (ID: {user_id})") # 로그 기록 (실제 비밀번호는 로그에 남기지 않도록 주의)

            # DB에 임시 비밀번호 업데이트 (!!! 중요: 해싱하여 저장 !!!)
            hashed_temp_password = generate_password_hash(temp_password)
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_temp_password, user_id))
            conn.commit()
            logger.info(f"Updated user {user_id}'s password in DB with hashed temporary password.")

            # 이메일 발송 (임시 비밀번호는 평문으로 보내야 함)
            email_subject = "임시 비밀번호 안내"
            email_body = f"""
안녕하세요, {user_name}님.

요청하신 임시 비밀번호는 다음과 같습니다:

{temp_password}

로그인 후 반드시 안전한 비밀번호로 변경해주세요.

감사합니다.
            """
            # send_email 헬퍼 함수 사용
            email_sent = send_email(email, email_subject, email_body)

            if not email_sent:
                # DB 업데이트는 성공했으나 이메일 발송 실패 시 처리 (롤백 또는 로깅 강화)
                logger.error(f"Failed to send temporary password email to {email} (User ID: {user_id})")
                # 사용자에게는 성공으로 응답하되, 관리자는 알 수 있도록 로깅
                # 또는 DB 롤백 후 에러 응답 고려
                # conn.rollback() # 롤백이 필요하다면 commit 전에 위치 조정 필요
                pass # 일단 이메일 실패는 로깅만 하고 넘어감

            # 이메일 존재 여부와 관계없이 성공 메시지 반환 (보안)
            return jsonify({'success': True, 'message': '입력하신 이메일 주소로 임시 비밀번호를 발송했습니다. 메일을 확인해주세요.'})
        else:
            # 사용자가 존재하지 않아도 동일한 성공 메시지 반환
            logger.info(f"Password reset requested for non-existent email: {email}")
            return jsonify({'success': True, 'message': '입력하신 이메일 주소로 임시 비밀번호를 발송했습니다. 메일을 확인해주세요.'})

    except sqlite3.Error as e:
        logger.error(f"Database error during password reset request for {email}: {e}", exc_info=True)
        if conn: conn.rollback() # 오류 발생 시 롤백
        return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
    except Exception as e:
        logger.error(f"Unexpected error during password reset request for {email}: {e}", exc_info=True)
        if conn: conn.rollback()
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500
    finally:
        if conn:
            conn.close()

# Route to handle sending verification email
@app.route('/api/send-verification', methods=['POST'])
def send_verification_email():
    data = request.get_json()
    email = data.get('email')

    if not email:
        logger.warning("[/api/send-verification] Email missing in request.")
        return jsonify({"success": False, "message": "이메일 주소를 입력해주세요."}), 400

    # Generate verification code
    code = ''.join(random.choices(string.digits, k=6)) # 6-digit code
    expires_at = datetime.now() + timedelta(minutes=10) # Code valid for 10 minutes

    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        # Insert or Replace allows sending a new code if requested again for the same email
        cursor.execute("""
            INSERT OR REPLACE INTO email_verifications (email, code, expires_at)
            VALUES (?, ?, ?)
        """, (email, code, expires_at))
        conn.commit()
        logger.info(f"Generated verification code {code} for email {email}, expires at {expires_at}")

        # Send email using the helper function
        subject = "회원가입 인증 코드"
        body = f"회원가입을 위한 인증 코드는 다음과 같습니다: {code}\n\n이 코드는 10분 후에 만료됩니다."
        email_sent = send_email(email, subject, body)

        if email_sent:
            return jsonify({"success": True, "message": "인증 코드가 이메일로 발송되었습니다."})
        else:
            # 실패 시의 메시지는 send_email 함수 로그를 기반으로 함
            # 좀 더 구체적인 오류 메시지를 원한다면 send_email 함수에서 오류 종류별로 다른 값을 반환하도록 수정 가능
            return jsonify({"success": False, "message": "인증 코드 발송 중 오류가 발생했습니다."}), 500

    except sqlite3.Error as e:
        logger.error(f"Database error storing verification code for {email}: {e}", exc_info=True)

# Route to verify the code entered by the user
@app.route('/api/verify-code', methods=['POST'])
def verify_code():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')

    if not email or not code:
        return jsonify({"success": False, "message": "이메일과 인증 코드를 모두 입력해주세요."}), 400

    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        # Use ISO format for timestamp comparison
        cursor.execute("SELECT code, strftime('%Y-%m-%dT%H:%M:%S', expires_at) FROM email_verifications WHERE email = ?", (email,))
        result = cursor.fetchone()

        if not result:
            logger.warning(f"Verification attempt for {email} failed: No code found or already verified.")
            return jsonify({"success": False, "message": "인증 코드가 요청되지 않았거나 만료되었습니다."}), 400

        stored_code, expires_at_str = result
        # Parse ISO format string
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
             # Fallback if timestamp format is slightly different (e.g., space instead of T)
             try:
                 expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
             except ValueError:
                 logger.error(f"Could not parse timestamp '{expires_at_str}' for email {email}")
                 return jsonify({"success": False, "message": "인증 코드 만료 시간 형식 오류."}), 500


        if datetime.now() > expires_at:
            logger.warning(f"Verification attempt for {email} failed: Code expired at {expires_at_str}")
            # Clean up expired code
            cursor.execute("DELETE FROM email_verifications WHERE email = ?", (email,))
            conn.commit()
            return jsonify({"success": False, "message": "인증 코드가 만료되었습니다. 다시 요청해주세요."}), 400

        if stored_code == code:
            # Verification successful, remove the code from DB
            cursor.execute("DELETE FROM email_verifications WHERE email = ?", (email,))
            conn.commit()
            logger.info(f"Email {email} successfully verified with code {code}.")
            # You might want to set a flag in the session here to indicate email verification
            # session['email_verified'] = True # Example
            # session['verified_email'] = email # Example
            return jsonify({"success": True, "message": "이메일 인증이 완료되었습니다."})
        else:
            logger.warning(f"Verification attempt for {email} failed: Invalid code entered.")
            return jsonify({"success": False, "message": "인증 코드가 올바르지 않습니다."}), 400

    except sqlite3.Error as e:
        logger.error(f"Database error verifying code for {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "인증 코드 확인 중 데이터베이스 오류 발생."}), 500
    except Exception as e:
        logger.error(f"Unexpected error verifying code for {email}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "인증 코드 확인 중 오류 발생."}), 500
    finally:
        if conn:
            conn.close()

# Route to handle actual signup process after verification
@app.route('/api/signup', methods=['POST'])
def signup_user():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        logger.warning("[/api/signup] Missing required fields (name, email, or password).")
        return jsonify({"success": False, "message": "이름, 이메일, 비밀번호를 모두 입력해주세요."}), 400

    # TODO (Optional but recommended): Verify if the email was recently verified.
    # This might require storing verification status temporarily (e.g., in session)
    # after /api/verify-code succeeds. For now, we proceed assuming verification happened.

    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            logger.warning(f"[/api/signup] Signup attempt with existing email: {email}")
            return jsonify({"success": False, "message": "이미 등록된 이메일 주소입니다."}), 409 # 409 Conflict is suitable

        # Hash the password before storing
        hashed_password = generate_password_hash(password)
        logger.debug(f"[/api/signup] Hashing password for user {email}")

        # Insert the new user
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                       (name, email, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid # Get the newly inserted user's ID
        logger.info(f"[/api/signup] User {email} (ID: {user_id}) signed up successfully.")

        # Optional: Log the user in immediately after signup
        # session['user_id'] = user_id
        # logger.info(f"[/api/signup] User {user_id} automatically logged in after signup.")

        return jsonify({"success": True, "message": "회원가입이 완료되었습니다. 로그인해주세요."}) # Or redirect if logged in

    except sqlite3.IntegrityError: # Catch potential unique constraint errors again (though check above helps)
        logger.warning(f"[/api/signup] IntegrityError (likely duplicate email) for email: {email}")
        return jsonify({"success": False, "message": "이미 등록된 이메일 주소입니다."}), 409
    except sqlite3.Error as e:
        logger.error(f"[/api/signup] Database error during signup for {email}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "회원가입 중 데이터베이스 오류가 발생했습니다."}), 500
    except Exception as e:
        logger.error(f"[/api/signup] Unexpected error during signup for {email}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "회원가입 중 오류가 발생했습니다."}), 500
    finally:
        if conn:
            conn.close()

# 사용자 비밀번호 변경 API
@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        # 이 경우는 @login_required 때문에 거의 발생하지 않지만, 안전하게 처리
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json()
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword') # 새 비밀번호 확인 필드

    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': '모든 비밀번호 필드를 입력해주세요.'}), 400

    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '새 비밀번호와 확인 비밀번호가 일치하지 않습니다.'}), 400

    # 비밀번호 복잡성 검사 (선택 사항, 필요 시 추가)
    # if len(new_password) < 8 or not any(c.isdigit() for c in new_password) ...:
    #     return jsonify({'success': False, 'message': '비밀번호는 8자 이상이어야 하며...'}), 400

    conn = None
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()

        # 현재 비밀번호 확인
        cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user:
            # 사용자를 찾을 수 없는 경우 (매우 드뭄)
            logger.error(f"Could not find user {user_id} during password change.")
            return jsonify({'success': False, 'message': '사용자 정보를 찾을 수 없습니다.'}), 404

        hashed_password_from_db = user[0]
        if not check_password_hash(hashed_password_from_db, current_password):
            logger.warning(f"Incorrect current password provided for user {user_id}")
            return jsonify({'success': False, 'message': '현재 비밀번호가 올바르지 않습니다.'}), 401

        # 새 비밀번호 해싱 및 업데이트
        new_hashed_password = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hashed_password, user_id))
        conn.commit()

        logger.info(f"User {user_id}'s password changed successfully.")
        return jsonify({'success': True, 'message': '비밀번호가 성공적으로 변경되었습니다.'})

    except sqlite3.Error as e:
        logger.error(f"Database error changing password for user {user_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
    except Exception as e:
        logger.error(f"Server error changing password for user {user_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500
    finally:
        if conn:
            conn.close()

def extract_location_parts(address):
    """
    주소 문자열에서 시/도(level1)와 구/군(level2)을 추출합니다.
    예: '서울특별시 강남구' -> ('서울특별시', '강남구')
    """
    if not address:
        return None, None
        
    parts = address.split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None

@app.route('/admin/demand-stats')
@login_required
@admin_required
def demand_stats_page():
    current_user = get_user_from_session()
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page'))

    # 필터 파라미터 가져오기 (HTML 폼 name과 일치시킴)
    region_filter = request.args.get('location_level1', '전체')
    district_filter = request.args.get('location_level2', '전체')
    status_filter = request.args.get('status', '전체')
    affiliated_center_filter = request.args.get('affiliated_center', '')
    org_name_filter = request.args.get('org_name', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # 지역별 시/군/구 데이터
    regions = {
        '서울특별시': ['강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'],
        '경기도': ['수원시', '성남시', '의정부시', '안양시', '부천시', '광명시', '평택시', '동두천시', '안산시', '고양시', '과천시', '구리시', '남양주시', '오산시', '시흥시', '군포시', '의왕시', '하남시', '용인시', '파주시', '이천시', '안성시', '김포시', '화성시', '광주시', '양주시', '포천시', '여주시', '연천군', '가평군', '양평군'],
        '인천광역시': ['중구', '동구', '미추홀구', '연수구', '남동구', '부평구', '계양구', '서구', '강화군', '옹진군'],
        '부산광역시': ['중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구', '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장군']
    }
    
    # 더미 데이터 생성 (100개)
    affiliated_centers = ['A센터', 'B센터', 'C센터', 'D센터']
    approved_centers = ['X센터', 'Y센터', 'Z센터']
    dummy_data = []
    for region, districts in regions.items():
        for _ in range(100):  # 각 지역별 100개씩
            district = random.choice(districts)
            status = random.choice(['승인', '반려', '대기'])
            affiliated_center = random.choice(affiliated_centers)
            approved_center = random.choice(approved_centers)
            org_name = f"{region} {district} 기관{random.randint(1, 100)}"
            date = (datetime(2025, 4, 1) + timedelta(days=random.randint(0, 40))).strftime('%Y-%m-%d')
            dummy_data.append({
                'region': region,
                'district': district,
                'status': status,
                'affiliated_center': affiliated_center,
                'approved_center': approved_center,
                'org_name': org_name,
                'date': date,
                'participants': random.randint(1, 100),
                'hours': random.randint(1, 200),
                'total_hours': random.randint(1, 20000),
                'total_participants': random.randint(1, 1000),
                'total_orgs': random.randint(1, 100)
            })
    
    # 필터링 적용
    filtered_data = dummy_data
    
    # 시/도 필터링
    if region_filter and region_filter != '전체':
        filtered_data = [d for d in filtered_data if d['region'] == region_filter]
    
    # 시/군/구 필터링
    if district_filter and district_filter != '전체':
        filtered_data = [d for d in filtered_data if d['district'] == district_filter]
    
    # 상태 필터링
    if status_filter and status_filter != '전체':
        filtered_data = [d for d in filtered_data if d['status'] == status_filter]
    
    # 기관명 검색
    if org_name_filter:
        filtered_data = [d for d in filtered_data if org_name_filter.lower() in d['org_name'].lower()]
    
    # 날짜 필터링
    if start_date and end_date:
        filtered_data = [d for d in filtered_data if start_date <= d['date'] <= end_date]
    
    # 소속센터 필터링
    if affiliated_center_filter:
        filtered_data = [d for d in filtered_data if affiliated_center_filter in d['affiliated_center']]
    
    # 필터링된 데이터를 stats_data에 할당
    stats_data = filtered_data
    
    # 필터 옵션 딕셔너리 생성
    filter_options = {
        'locations_structured': regions,
        'statuses': {
            '전체': '전체',
            '승인': '승인',
            '반려': '반려',
            '대기': '대기'
        }
    }

    # search_params 딕셔너리 생성 (템플릿에서 사용)
    search_params = {
        'location_level1': region_filter,
        'location_level2': district_filter,
        'status': status_filter,
        'org_name': org_name_filter,
        'start_date': start_date,
        'end_date': end_date,
        'affiliated_center': affiliated_center_filter
    }
    
    print(f"stats_data count: {len(stats_data)}")  # 디버깅용 출력
    
    return render_template('demand_center_stats.html', 
                         current_user=current_user,
                         stats_data=stats_data,
                         regions=regions,
                         filter_options=filter_options,
                         search_params=search_params,
                         selected_region=region_filter,
                         selected_district=district_filter,
                         selected_status=status_filter,
                         org_name_filter=org_name_filter,
                         start_date=start_date,
                         end_date=end_date,
                         page_type='demand_stats')

@app.route('/admin/record-performance') # URL은 유지하되, 접근 권한 변경
@login_required # 로그인된 사용자만 접근 가능
# @admin_required # <- 이 데코레이터 제거
def record_performance_page():
    current_user = get_user_from_session()
    # page_type 전달은 유지
    # ... (기존 함수 내용 동일) ...
    conn_v = None
    conn_u = None
    approved_applications = []
    admin_org_map = {}

    try:
        conn_v = sqlite3.connect(VOLUNTEER_DB_PATH)
        conn_v.row_factory = sqlite3.Row
        cursor_v = conn_v.cursor()
        
        cursor_v.execute("""SELECT 
                           va.id as application_id,
                           va.applicant_name,
                           va.applicant_email,
                           v.activity_title,
                           v.volunteer_content,
                           va.volunteer_date,
                           v.activity_time_start,
                           v.activity_time_end,
                           v.credited_hours,
                           v.user_id as admin_user_id,
                           va.performance_status,
                           va.performance_rejection_reason
                       FROM volunteer_applications va
                       JOIN volunteers v ON va.volunteer_id = v.id
                       WHERE va.status = 'approved' 
                       ORDER BY va.application_date DESC""")
        applications_raw = cursor_v.fetchall()
        
        admin_ids = list(set(app['admin_user_id'] for app in applications_raw if app['admin_user_id']))

        if admin_ids:
            conn_u = sqlite3.connect(USERS_DB_PATH)
            conn_u.row_factory = sqlite3.Row # admin_verifications 테이블 접근 시에도 row_factory 사용
            cursor_u = conn_u.cursor()
            placeholders = ','.join('?' * len(admin_ids))
            cursor_u.execute(f"""SELECT user_id, organization 
                                FROM admin_verifications 
                                WHERE user_id IN ({placeholders}) AND status = 'approved'""", 
                             tuple(admin_ids))
            for row in cursor_u.fetchall():
                 admin_org_map[row[0]] = row[1]

        for app in applications_raw:
            app_dict = dict(app)
            admin_id = app_dict.get('admin_user_id')
            app_dict['admin_org_name'] = admin_org_map.get(admin_id, '기관 정보 없음')
            approved_applications.append(app_dict)

    except sqlite3.Error as e:
        logger.error(f"실적 등록 페이지 데이터 조회 중 DB 오류: {str(e)}", exc_info=True)
        flash("데이터 조회 중 오류가 발생했습니다.", "error")
    except Exception as e:
        logger.error(f"실적 등록 페이지 데이터 조회 중 서버 오류: {str(e)}", exc_info=True)
        flash("데이터 조회 중 오류가 발생했습니다.", "error")
    finally:
        if conn_v:
            conn_v.close()
        if conn_u:
            conn_u.close()

    return render_template('record_performance.html',
                           current_user=current_user,
                           applications=approved_applications,
                           page_type='record_performance')

@app.route('/api/admin/process-performance', methods=['POST'])
@login_required
@admin_required
def process_performance():
    data = request.get_json()
    application_ids = data.get('ids')
    action = data.get('action') # 'register' 또는 'reject'
    reason = data.get('reason') # 반려 시 사유

    if not application_ids or not action or action not in ['register', 'reject']:
        logger.warning(f"Invalid data received for performance processing: {data}")
        return jsonify({'success': False, 'message': '잘못된 요청 데이터입니다.'}), 400

    if action == 'reject' and not reason:
        return jsonify({'success': False, 'message': '반려 사유를 입력해야 합니다.'}), 400

    conn_v = None
    processed_count = 0
    try:
        conn_v = sqlite3.connect(VOLUNTEER_DB_PATH)
        cursor_v = conn_v.cursor()
        
        placeholders = ','.join('?' * len(application_ids))
        
        if action == 'reject':
            # 'approved' 상태이고 아직 실적 처리되지 않은('pending') 신청 건만 반려 처리
            sql = f"""UPDATE volunteer_applications 
                      SET performance_status = 'rejected',
                          performance_rejection_reason = ? 
                      WHERE id IN ({placeholders}) 
                      AND status = 'approved' 
                      AND (performance_status = 'pending' OR performance_status IS NULL)""" # performance_status IS NULL 조건 추가
            params = [reason] + application_ids
            message_verb = "반려"
        elif action == 'register':
            # TODO: 실적 등록 로직 구현 (실제 시간 등 필요)
            # 임시: 상태만 변경 (추후 수정 필요)
            sql = f"""UPDATE volunteer_applications 
                      SET performance_status = 'recorded' 
                      WHERE id IN ({placeholders}) 
                      AND status = 'approved' 
                      AND (performance_status = 'pending' OR performance_status IS NULL)""" # performance_status IS NULL 조건 추가
            params = application_ids
            message_verb = "실적 등록"
            logger.warning("'register' action called but only updates status temporarily. Full implementation needed.")
        
        cursor_v.execute(sql, params)
        processed_count = cursor_v.rowcount
        conn_v.commit()
        logger.info(f"{processed_count} applications processed with action '{action}'. IDs: {application_ids}")
        
        return jsonify({'success': True, 'message': f'{processed_count}건의 신청이 {message_verb} 처리되었습니다.', 'processed_count': processed_count})

    except sqlite3.Error as e:
        logger.error(f"실적 처리 중 데이터베이스 오류: {str(e)}", exc_info=True)
        if conn_v:
            conn_v.rollback()
        return jsonify({'success': False, 'message': '데이터베이스 오류가 발생했습니다.'}), 500
    except Exception as e:
        logger.error(f"실적 처리 중 서버 오류: {str(e)}", exc_info=True)
        if conn_v:
            conn_v.rollback()
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500
    finally:
        if conn_v:
            conn_v.close()
            
if __name__ == '__main__':
    # 모든 인터페이스에서 접속 가능하도록 호스트 변경
    app.run(host='0.0.0.0', port=5000, debug=True) 