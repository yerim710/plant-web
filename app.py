from flask import Flask, request, jsonify, send_from_directory
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

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

# 정적 파일 제공
@app.route('/')
def index():
    return send_from_directory('.', 'login.html')

@app.route('/signup')
def signup_page():
    return send_from_directory('.', 'signup.html')

@app.route('/main')
def main_page():
    return send_from_directory('.', 'main.html')

# CSS 파일 제공
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# 인증 코드 저장소
verification_codes = {}

# 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         name TEXT NOT NULL,
         email TEXT UNIQUE NOT NULL,
         password TEXT NOT NULL)
    ''')
    
    # verification_codes 테이블 생성
    c.execute('''
        CREATE TABLE IF NOT EXISTS verification_codes
        (email TEXT PRIMARY KEY,
         code TEXT NOT NULL,
         created_at TIMESTAMP NOT NULL)
    ''')
    
    conn.commit()
    conn.close()

# 데이터베이스 초기화 실행
init_db()

# 인증 코드 생성 함수
def generate_verification_code():
    # 영문과 숫자 조합으로 6자리 코드 생성
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=6))

# 이메일 설정
SMTP_SERVER = "smtp.naver.com"
SMTP_PORT = 465
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(to_email, subject, body):
    try:
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            raise ValueError("SMTP_USERNAME 또는 SMTP_PASSWORD 환경 변수가 설정되지 않았습니다.")

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"이메일 전송 오류: {str(e)}")
        return False

@app.route('/api/send-verification', methods=['POST', 'OPTIONS'])
def send_verification():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
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
        print(f"인증 코드 전송 오류: {str(e)}")
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
        안녕하세요,
        
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
            'message': '회원가입이 완료되었습니다. 이메일로 전송된 인증 코드를 확인해주세요.'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password = ?',
                 (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            return jsonify({
                'success': True,
                'message': '로그인 성공',
                'user': {
                    'id': user[0],
                    'name': user[1],
                    'email': user[2]
                }
            })
        else:
            return jsonify({'success': False, 'message': '이메일 또는 비밀번호가 일치하지 않습니다.'}), 401

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/volunteer', methods=['POST'])
def add_volunteer():
    try:
        title = request.form.get('title')
        date = request.form.get('date')
        location = request.form.get('location')
        locationDetail = request.form.get('locationDetail')
        description = request.form.get('description')
        
        # 이미지 파일 처리
        image = request.files.get('image')
        image_path = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join('static', image_path))
            image_path = f'/static/{image_path}'

        # 데이터베이스에 저장
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO volunteers (title, date, location, locationDetail, description, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, date, location, locationDetail, description, image_path))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '봉사활동이 등록되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 이미지 업로드를 위한 디렉토리 생성
os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)

# 게시판 관련 API
@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, author, created_at, views 
            FROM posts 
            ORDER BY created_at DESC
        ''')
        posts = cursor.fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'posts': [{
                'id': post[0],
                'title': post[1],
                'author': post[2],
                'created_at': post[3],
                'views': post[4]
            } for post in posts]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/posts', methods=['POST'])
def create_post():
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        author = request.form.get('author')
        image = request.files.get('image')

        if not all([title, content, author]):
            return jsonify({'success': False, 'message': '모든 필드를 입력해주세요.'}), 400

        image_path = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join('static', image_path))
            image_path = f'/static/{image_path}'

        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO posts (title, content, author, created_at, views, image_path)
            VALUES (?, ?, ?, datetime('now'), 0, ?)
        ''', (title, content, author, image_path))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '게시글이 등록되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE posts SET views = views + 1 WHERE id = ?
        ''', (post_id,))
        cursor.execute('''
            SELECT id, title, content, author, created_at, views, image_path 
            FROM posts 
            WHERE id = ?
        ''', (post_id,))
        post = cursor.fetchone()
        conn.commit()
        conn.close()

        if post:
            return jsonify({
                'success': True,
                'post': {
                    'id': post[0],
                    'title': post[1],
                    'content': post[2],
                    'author': post[3],
                    'created_at': post[4],
                    'views': post[5],
                    'image_path': post[6]
                }
            })
        else:
            return jsonify({'success': False, 'message': '게시글을 찾을 수 없습니다.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 식물 관련 API
@app.route('/api/plants', methods=['GET'])
def get_plants():
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                watering_frequency INTEGER NOT NULL,
                last_watered DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('SELECT * FROM plants ORDER BY created_at DESC')
        plants = cursor.fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'plants': [{
                'id': plant[0],
                'name': plant[1],
                'species': plant[2],
                'watering_frequency': plant[3],
                'last_watered': plant[4],
                'created_at': plant[5]
            } for plant in plants]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/plants', methods=['POST'])
def create_plant():
    try:
        data = request.json
        name = data.get('name')
        species = data.get('species')
        watering_frequency = data.get('watering_frequency')

        if not all([name, species, watering_frequency]):
            return jsonify({'success': False, 'message': '모든 필드를 입력해주세요.'}), 400

        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO plants (name, species, watering_frequency, last_watered)
            VALUES (?, ?, ?, datetime('now'))
        ''', (name, species, watering_frequency))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '식물이 등록되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/plants/<int:plant_id>/water', methods=['POST'])
def water_plant(plant_id):
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE plants 
            SET last_watered = datetime('now')
            WHERE id = ?
        ''', (plant_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '물주기가 완료되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/plants/<int:plant_id>', methods=['DELETE'])
def delete_plant(plant_id):
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM plants WHERE id = ?', (plant_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '식물이 삭제되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect('volunteer.db')
    cursor = conn.cursor()
    
    # 봉사활동 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            locationDetail TEXT NOT NULL,
            description TEXT NOT NULL,
            image_path TEXT
        )
    ''')
    
    # 게시판 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            views INTEGER DEFAULT 0,
            image_path TEXT
        )
    ''')
    
    # 식물 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT NOT NULL,
            watering_frequency INTEGER NOT NULL,
            last_watered DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 테스트 데이터 추가
    cursor.execute('''
        INSERT OR IGNORE INTO volunteers (title, date, location, locationDetail, description)
        VALUES (?, ?, ?, ?, ?)
    ''', ('테스트 봉사활동', '2024-03-20', '서울시 강남구', '강남역 1번 출구', '이것은 테스트 봉사활동입니다.'))
    
    cursor.execute('''
        INSERT OR IGNORE INTO posts (title, content, author, created_at, views)
        VALUES (?, ?, ?, datetime('now'), 0)
    ''', ('테스트 게시글', '이것은 테스트 게시글입니다.', 'test@example.com'))
    
    cursor.execute('''
        INSERT OR IGNORE INTO plants (name, species, watering_frequency, last_watered)
        VALUES (?, ?, ?, datetime('now'))
    ''', ('테스트 식물', '선인장', 7))
    
    conn.commit()
    conn.close()

# 데이터베이스 초기화
init_db()

# 봉사활동 관련 API
@app.route('/api/volunteers', methods=['GET'])
def get_volunteers():
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM volunteers ORDER BY date DESC')
        volunteers = cursor.fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'volunteers': [{
                'id': volunteer[0],
                'title': volunteer[1],
                'date': volunteer[2],
                'location': volunteer[3],
                'locationDetail': volunteer[4],
                'description': volunteer[5],
                'image_path': volunteer[6]
            } for volunteer in volunteers]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/volunteers', methods=['POST'])
def create_volunteer():
    try:
        title = request.form.get('title')
        date = request.form.get('date')
        location = request.form.get('location')
        locationDetail = request.form.get('locationDetail')
        description = request.form.get('description')
        image = request.files.get('image')

        if not all([title, date, location, locationDetail, description]):
            return jsonify({'success': False, 'message': '모든 필드를 입력해주세요.'}), 400

        image_path = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join('static', image_path))
            image_path = f'/static/{image_path}'

        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO volunteers (title, date, location, locationDetail, description, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, date, location, locationDetail, description, image_path))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '봉사활동이 등록되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/volunteers/<int:volunteer_id>', methods=['GET'])
def get_volunteer(volunteer_id):
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM volunteers WHERE id = ?', (volunteer_id,))
        volunteer = cursor.fetchone()
        conn.close()

        if volunteer:
            return jsonify({
                'success': True,
                'volunteer': {
                    'id': volunteer[0],
                    'title': volunteer[1],
                    'date': volunteer[2],
                    'location': volunteer[3],
                    'locationDetail': volunteer[4],
                    'description': volunteer[5],
                    'image_path': volunteer[6]
                }
            })
        else:
            return jsonify({'success': False, 'message': '봉사활동을 찾을 수 없습니다.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/volunteers/<int:volunteer_id>', methods=['DELETE'])
def delete_volunteer(volunteer_id):
    try:
        conn = sqlite3.connect('volunteer.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM volunteers WHERE id = ?', (volunteer_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '봉사활동이 삭제되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 