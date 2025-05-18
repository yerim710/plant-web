import sqlite3
from werkzeug.security import generate_password_hash

def create_admin_account():
    # Connect to Flask's users.db
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Add is_admin column if it doesn't exist
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0')
        conn.commit()
        print("Added is_admin column to users table")
    except sqlite3.OperationalError:
        print("is_admin column already exists")
    
    # Add admin account
    admin_email = 'admin@test.com'
    admin_password = 'admin123'  # Change this to your desired password
    hashed_password = generate_password_hash(admin_password)
    
    try:
        cursor.execute('''
        INSERT INTO users (email, password, name, is_admin)
        VALUES (?, ?, ?, ?)
        ''', (admin_email, hashed_password, 'Admin', 1))
        conn.commit()
        print(f"Admin account {admin_email} created successfully!")
    except sqlite3.IntegrityError:
        print(f"Admin account {admin_email} already exists!")
    finally:
        conn.close()

if __name__ == '__main__':
    create_admin_account() 