import sqlite3
import os
import json

DB_PATH = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # جدول الفئات
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            keywords TEXT
        )
    ''')
    # جدول الأصناف
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            images TEXT,
            videos TEXT,
            pdf TEXT,
            price TEXT,
            discount TEXT,
            specs TEXT,
            keywords TEXT,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    # جدول الأوراق
    conn.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            keywords TEXT
        )
    ''')
    # محاولة إضافة الأعمدة الناقصة (Migration)
    try:
        conn.execute('ALTER TABLE items ADD COLUMN category_id INTEGER')
    except: pass
    try:
        conn.execute('ALTER TABLE items ADD COLUMN keywords TEXT')
    except: pass
    try:
        conn.execute('ALTER TABLE categories ADD COLUMN keywords TEXT')
    except: pass
        
    conn.commit()
    conn.close()

# --- عمليات الفئات (Categories) ---
def add_category(name, keywords):
    conn = get_db_connection()
    conn.execute('INSERT INTO categories (name, keywords) VALUES (?, ?)', (name, keywords))
    conn.commit()
    conn.close()

def get_all_categories():
    conn = get_db_connection()
    cats = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    return cats

def delete_category(cat_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
    # اختيارياً: مسح الأصناف التابعة لهذه الفئة أو جعل فئتها NULL
    conn.execute('UPDATE items SET category_id = NULL WHERE category_id = ?', (cat_id,))
    conn.commit()
    conn.close()

# --- عمليات الأصناف (Items) ---
def add_item(name, description, images, videos, pdf, price, discount, specs, category_id, keywords):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO items (name, description, images, videos, pdf, price, discount, specs, category_id, keywords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, json.dumps(images), json.dumps(videos), pdf, price, discount, json.dumps(specs), category_id, keywords))
    conn.commit()
    conn.close()

def get_all_items():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT items.*, categories.name as category_name 
        FROM items 
        LEFT JOIN categories ON items.category_id = categories.id
    ''').fetchall()
    conn.close()
    items = []
    for row in rows:
        item = dict(row)
        item['images'] = json.loads(item['images']) if item['images'] else []
        item['videos'] = json.loads(item['videos']) if item['videos'] else []
        item['specs'] = json.loads(item['specs']) if item['specs'] else {}
        items.append(item)
    return items

def get_items_by_category(category_id):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM items WHERE category_id = ?', (category_id,)).fetchall()
    conn.close()
    items = []
    for row in rows:
        item = dict(row)
        item['images'] = json.loads(item['images']) if item['images'] else []
        item['videos'] = json.loads(item['videos']) if item['videos'] else []
        item['specs'] = json.loads(item['specs']) if item['specs'] else {}
        items.append(item)
    return items

def get_item_by_id(item_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    if row:
        item = dict(row)
        item['images'] = json.loads(item['images']) if item['images'] else []
        item['videos'] = json.loads(item['videos']) if item['videos'] else []
        item['specs'] = json.loads(item['specs']) if item['specs'] else {}
        return item
    return None

def delete_item(item_id):
    conn = get_db_connection()
    item = get_item_by_id(item_id)
    if item:
        all_files = item['images'] + item['videos'] + ([item['pdf']] if item['pdf'] else [])
        for f in all_files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
    conn.close()

# --- عمليات الأوراق ---
def add_document(name, file_path, keywords):
    conn = get_db_connection()
    conn.execute('INSERT INTO documents (name, file_path, keywords) VALUES (?, ?, ?)', (name, file_path, keywords))
    conn.commit()
    conn.close()

def get_all_documents():
    conn = get_db_connection()
    docs = conn.execute('SELECT * FROM documents').fetchall()
    conn.close()
    return docs

def delete_document(doc_id):
    conn = get_db_connection()
    doc = conn.execute('SELECT file_path FROM documents WHERE id = ?', (doc_id,)).fetchone()
    if doc:
        if os.path.exists(doc['file_path']):
            try: os.remove(doc['file_path'])
            except: pass
        conn.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        conn.commit()
    conn.close()

def get_document_by_id(doc_id):
    conn = get_db_connection()
    doc = conn.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
    conn.close()
    return doc

import re
def normalize_arabic(text):
    if not text: return ""
    text = re.sub(r'[\u064B-\u0652]', '', text)
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    return text.strip().lower()
