import sqlite3
from datetime import datetime
import pandas as pd
import os

DB_NAME = "messages.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            message TEXT,
            name TEXT,
            position TEXT,
            is_anonymous INTEGER,
            reason TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'Ожидает ответа',
            answer TEXT DEFAULT '',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_message(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (
            user_id, type, message, name, position,
            is_anonymous, reason, file_path, status, answer, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["type"],
        data["message"],
        data["name"],
        data["position"],
        data.get("is_anonymous", 0),
        data.get("reason", ""),
        data.get("file_path"),
        "Ожидает ответа",
        "",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def get_user_messages(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, type, message, status, answer
        FROM messages
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results


def get_message_by_id(message_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def update_status_and_response(message_id, status, answer):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE messages
        SET status = ?, answer = ?
        WHERE id = ?
    """, (status, answer, message_id))
    conn.commit()
    conn.close()


def export_all_messages(file_path="exported_messages.xlsx"):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM messages", conn)
    conn.close()
    df.to_excel(file_path, index=False)
    return os.path.abspath(file_path)


def get_all_messages():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, type, message, status
        FROM messages
        ORDER BY created_at DESC
    """)
    results = cursor.fetchall()
    conn.close()
    return results
