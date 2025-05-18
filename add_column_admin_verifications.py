import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# 컬럼 추가 함수 (이미 있으면 무시)
def add_column_if_not_exists(table, column, col_type):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
        print(f"컬럼 추가됨: {column}")
    except Exception as e:
        print(f"{column}: {e}")

add_column_if_not_exists('admin_verifications', 'organization_type', 'TEXT')
add_column_if_not_exists('admin_verifications', 'manager_position', 'TEXT')
add_column_if_not_exists('admin_verifications', 'manager_email', 'TEXT')
add_column_if_not_exists('admin_verifications', 'main_activities', 'TEXT')
add_column_if_not_exists('admin_verifications', 'manager_name', 'TEXT')
add_column_if_not_exists('admin_verifications', 'business_number', 'TEXT')
add_column_if_not_exists('admin_verifications', 'manager_phone', 'TEXT')

conn.commit()
conn.close()
print("컬럼 추가 완료") 