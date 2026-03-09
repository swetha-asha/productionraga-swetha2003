import sqlite3
import json

DATABASE_PATH = "vectors.db"

def get_connection():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vectors(
        id INTEGER PRIMARY KEY,
        text TEXT,
        embedding TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users(username, password) VALUES (?,?)", (username, password))
        conn.commit()
    except Exception as e:
        print(f"Error adding user: {e}")
    conn.close()

def get_user_password(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def update_user_password(username, new_password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
    conn.commit()
    conn.close()

def insert_vector(text, embedding):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO vectors(text, embedding) VALUES (?,?)",
        (text, json.dumps(embedding))
    )
    conn.commit()
    conn.close()

def get_vectors():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT text, embedding FROM vectors")
    rows = cursor.fetchall()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "text": r[0],
            "embedding": json.loads(r[1])
        })
    return data

# Initialize the database on import
init_db()
