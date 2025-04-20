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
from werkzeug.security import check_password_hash
import pandas as pd
from io import BytesIO
from functools import wraps
import json

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

# 관리자 확인 데코레이터 (원래 로직: 'approved' 상태 확인)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('login_page', next=request.url))
        
        user_id = session['user_id']
        logger.debug(f"[@admin_required] Checking admin status for user_id: {user_id}") # 로그 추가
        conn = None
        is_approved_admin = False
        try:
            conn = sqlite3.connect(USERS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status FROM admin_verifications 
                WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            result = cursor.fetchone()
            if result and result[0] == 'approved': # status 값 직접 비교
                is_approved_admin = True
            logger.debug(f"[@admin_required] DB check result for user_id {user_id}: Status='{result[0] if result else None}', is_approved_admin={is_approved_admin}") # 로그 추가
        except Exception as e:
            logger.error(f"Admin check failed for user {user_id}: {str(e)}", exc_info=True)
        finally:
            if conn:
                conn.close()
                
        if not is_approved_admin:
            logger.warning(f"[@admin_required] Admin access denied for user_id: {user_id}") # 로그 추가
            flash('관리자 인증이 필요합니다.', 'warning')
            return redirect(url_for('main_page')) 
            
        logger.debug(f"[@admin_required] Admin access granted for user_id: {user_id}") # 로그 추가
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
        # Include is_admin check (based on approved verification)
        cursor.execute("""
            SELECT u.id, u.name, u.email, 
                   CASE WHEN EXISTS (SELECT 1 FROM admin_verifications av WHERE av.user_id = u.id AND av.status = 'approved') THEN 1 ELSE 0 END as is_admin
            FROM users u 
            WHERE u.id = ?
        """, (user_id,))
        user_info = cursor.fetchone()
        if user_info:
             logger.debug(f"get_user_from_session: Found user info for ID {user_id}: Name={user_info['name']}, Email={user_info['email']}, IsAdmin={user_info['is_admin']}")
        else:
             logger.warning(f"get_user_from_session: User info not found in DB for ID {user_id}")
        return user_info # Returns Row object or None
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
    current_user = get_user_from_session() # Use helper function
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error") # More specific message
        return redirect(url_for('login_page'))
    # Pass the fetched user info to the template
    return render_template('main.html', current_user=current_user)

@app.route('/register-volunteer')
@login_required
@admin_required # Only approved admins can access this page anyway
def register_volunteer_page():
    current_user = get_user_from_session() # Use helper function
    if not current_user:
        # This case is less likely due to decorators, but handle defensively
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page')) 
    # Pass the fetched user info to the template
    return render_template('register_volunteer.html', current_user=current_user)

@app.route('/manage-volunteers')
@login_required
def manage_volunteers_page():
    current_user = get_user_from_session() # Use helper function
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page'))
        
    conn_v = None
    applications = []
    try:
        conn_v = sqlite3.connect(VOLUNTEER_DB_PATH)
        conn_v.row_factory = sqlite3.Row
        cursor_v = conn_v.cursor()
        # Fetch applications joining with volunteers table
        cursor_v.execute("""SELECT va.id, va.applicant_name, va.applicant_email, v.activity_title, va.volunteer_date, va.application_date, va.status FROM volunteer_applications va JOIN volunteers v ON va.volunteer_id = v.id ORDER BY va.application_date DESC""")
        applications = cursor_v.fetchall()
        logger.debug(f"Fetched {len(applications)} volunteer applications with titles.")
    except sqlite3.Error as e:
        logger.error(f"봉사 신청 목록 조회 중 데이터베이스 오류: {str(e)}", exc_info=True)
        flash("신청 목록을 불러오는 중 오류가 발생했습니다.", "error")
    except Exception as e:
        logger.error(f"봉사 신청 목록 조회 중 서버 오류: {str(e)}", exc_info=True)
        flash("신청 목록을 불러오는 중 오류가 발생했습니다.", "error")
    finally:
        if conn_v:
            conn_v.close()
            
    # Pass current_user along with applications
    return render_template('manage_volunteers.html', applications=applications, current_user=current_user, body_class='manage-volunteers-page') 

@app.route('/profile')
@login_required
def profile_page():
    current_user = get_user_from_session() # Use helper function
    if not current_user:
        flash("사용자 정보를 불러올 수 없습니다. 다시 로그인 해주세요.", "error")
        return redirect(url_for('login_page'))
    # Pass user info to template, e.g., for sidebar logic or pre-filling forms if needed
    return render_template('profile.html', current_user=current_user)

@app.route('/admin-verification')
@login_required # Ensure user is logged in
def admin_verification():
    current_user = get_user_from_session() # Use helper function
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
        # Fetch the latest verification attempt for this user
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
            
    # Pass current_user (contains name, email, is_admin) and verification status
    return render_template('admin_verification.html', verification=verification, current_user=current_user)

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
@login_required # Base login check
@admin_required # Ensures user has 'approved' status (but might not be admin@test.com)
def approve_requests_page():
    current_user = get_user_from_session() # Use helper function
    # Specific check for the super admin email
    if not current_user or current_user['email'] != 'admin@test.com': 
        flash("이 페이지에 접근할 권한이 없습니다.", "warning") # Changed message and category
        return redirect(url_for('main_page'))
        
    # ... (rest of the logic fetching pending_requests, counts remains the same) ...
    conn = None
    pending_requests = []
    admin_count = 0
    user_count = 0
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Fetch pending requests
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
        # Fetch counts
        cursor.execute("SELECT COUNT(id) FROM admin_verifications WHERE status = 'approved'")
        admin_count_result = cursor.fetchone()
        admin_count = admin_count_result[0] if admin_count_result else 0
        cursor.execute("SELECT COUNT(id) FROM users")
        user_count_result = cursor.fetchone()
        user_count = user_count_result[0] if user_count_result else 0
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
                           current_user=current_user, # Already passing correct user info
                           admin_count=admin_count,
                           user_count=user_count,
                           page_type='admin_approval') # Keep page type for active class

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
    pass # TODO: 복원 필요
    user_id = session.get('user_id')
    # ... (기존 이메일 변경 로직 복원) ...

# 사용자 비밀번호 변경 API
@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    pass # TODO: 복원 필요
    # ... (기존 비밀번호 변경 로직 복원) ...

# 회원 탈퇴 API
@app.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    conn_users = None
    conn_volunteer = None
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
    try:
        conn = sqlite3.connect(VOLUNTEER_DB_PATH)
        conn.row_factory = sqlite3.Row # 딕셔너리처럼 접근 가능하게
        cursor = conn.cursor()

        # 해당 ID의 봉사활동 데이터 조회
        cursor.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,))
        volunteer_data = cursor.fetchone()

        if not volunteer_data:
            flash('수정할 봉사 활동 정보를 찾을 수 없습니다.', 'error')
            return redirect(url_for('main_page')) # 또는 적절한 오류 페이지

        # 조회된 데이터를 템플릿에 전달
        return render_template('edit_volunteer.html', volunteer=volunteer_data)

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

if __name__ == '__main__':
    # 호스트를 127.0.0.1로 변경하여 로컬에서만 실행
    app.run(host='127.0.0.1', port=5000, debug=True) 