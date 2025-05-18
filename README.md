# Plant - 봉사활동 관리 시스템

Plant는 봉사활동을 관리하고 기록하는 웹 기반 시스템입니다. 사용자들은 봉사활동을 등록하고, 신청하고, 실적을 관리할 수 있습니다.

## 주요 기능

- 사용자 관리 (회원가입, 로그인, 비밀번호 재설정)
- 관리자 인증 시스템
- 봉사활동 등록 및 관리
- 봉사활동 신청 및 승인
- 실적 관리 및 기록
- 통계 및 보고서 생성

## 기술 스택

- Backend: Python Flask
- Database: SQLite
- Frontend: HTML, CSS, JavaScript
- Email: Flask-Mail

## 설치 및 실행 방법

1. 저장소 클론

```bash
git clone [repository-url]
cd [repository-name]
```

2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

4. 데이터베이스 초기화

```bash
python create_admin.py
```

5. 서버 실행

```bash
python app.py
```

## 환경 설정

- `app.py`에서 이메일 설정을 수정해야 합니다.
- 데이터베이스 파일은 자동으로 생성됩니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
