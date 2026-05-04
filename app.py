import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from database import (
    init_db, add_item, get_all_items, delete_item, get_item_by_id,
    add_document, get_all_documents, delete_document, get_document_by_id,
    add_category, get_all_categories, delete_category
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'category-secret-123')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

init_db()

def save_file(file, subfolder):
    if not file: return None
    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(path, exist_ok=True)
    base, ext = os.path.splitext(filename)
    full_path = os.path.join(path, filename)
    counter = 1
    while os.path.exists(full_path):
        filename = f"{base}_{counter}{ext}"
        full_path = os.path.join(path, filename)
        counter += 1
    file.save(full_path)
    return full_path

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('items_page'))
        flash('خطأ في البيانات')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- الفئات (Categories) ---
@app.route('/categories')
def categories_page():
    if not session.get('logged_in'): return redirect(url_for('login'))
    categories = get_all_categories()
    return render_template('categories.html', categories=categories)

@app.route('/categories/add', methods=['POST'])
def add_category_route():
    if not session.get('logged_in'): return redirect(url_for('login'))
    name = request.form.get('name')
    keywords = request.form.get('keywords')
    if name:
        add_category(name, keywords)
        flash('تمت إضافة الفئة!')
    return redirect(url_for('categories_page'))

@app.route('/categories/delete/<int:cat_id>')
def delete_category_route(cat_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    delete_category(cat_id)
    flash('تم حذف الفئة')
    return redirect(url_for('categories_page'))

# --- الأصناف (Items) ---
@app.route('/')
@app.route('/items')
def items_page():
    if not session.get('logged_in'): return redirect(url_for('login'))
    items = get_all_items()
    categories = get_all_categories()
    return render_template('items.html', items=items, categories=categories)

@app.route('/items/add', methods=['POST'])
def add_item_route():
    if not session.get('logged_in'): return redirect(url_for('login'))
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    discount = request.form.get('discount')
    category_id = request.form.get('category_id')
    image_files = request.files.getlist('images')
    image_paths = [save_file(f, 'images') for f in image_files if f.filename]
    video_files = request.files.getlist('videos')
    video_paths = [save_file(f, 'videos') for f in video_files if f.filename]
    pdf_file = request.files.get('pdf')
    pdf_path = save_file(pdf_file, 'pdfs') if pdf_file and pdf_file.filename else None
    specs_raw = request.form.get('specs', '{}')
    keywords = request.form.get('keywords')
    try: specs = json.loads(specs_raw)
    except: specs = {}
    add_item(name, description, image_paths, video_paths, pdf_path, price, discount, specs, category_id, keywords)
    flash('تمت إضافة المنتج!')
    return redirect(url_for('items_page'))

@app.route('/items/delete/<int:item_id>')
def delete_item_route(item_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    delete_item(item_id)
    flash('تم حذف المنتج')
    return redirect(url_for('items_page'))

# --- الأوراق ---
@app.route('/documents')
def documents_page():
    if not session.get('logged_in'): return redirect(url_for('login'))
    documents = get_all_documents()
    return render_template('documents.html', documents=documents)

@app.route('/documents/add', methods=['POST'])
def add_document_route():
    if not session.get('logged_in'): return redirect(url_for('login'))
    name = request.form.get('name')
    keywords = request.form.get('keywords')
    file = request.files.get('file')
    if file:
        file_path = save_file(file, 'docs')
        add_document(name, file_path, keywords)
        flash('تمت إضافة الورقة!')
    return redirect(url_for('documents_page'))

@app.route('/documents/delete/<int:doc_id>')
def delete_document_route(doc_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    delete_document(doc_id)
    flash('تم حذف الورقة')
    return redirect(url_for('documents_page'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
