import os
import json
import re
import firebase_admin
from firebase_admin import credentials, firestore

# تهيئة Firebase
# يحاول الكود البحث عن ملف firebase_key.json أو استخدام متغير بيئة
cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'firebase_key.json')

if not firebase_admin._apps:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        # إذا لم يوجد الملف، يمكن استخدام متغير البيئة (مفيد لـ Railway)
        try:
            cred_json = os.getenv('FIREBASE_CONFIG')
            if cred_json:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            else:
                print("Warning: Firebase configuration not found. Use FIREBASE_CONFIG env var or firebase_key.json")
        except Exception as e:
            print(f"Error initializing Firebase: {e}")

db = firestore.client()

def init_db():
    # في Firestore لا نحتاج لإنشاء جداول مسبقاً
    pass

def normalize_arabic(text):
    if not text: return ""
    text = re.sub(r'[\u064B-\u0652]', '', text)
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    return text.strip().lower()

# --- عمليات الفئات (Categories) ---
def add_category(name, keywords):
    db.collection('categories').add({
        'name': name,
        'keywords': keywords
    })

def get_all_categories():
    docs = db.collection('categories').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def delete_category(cat_id):
    db.collection('categories').document(cat_id).delete()
    # تحديث الأصناف التي تتبع هذه الفئة
    items = db.collection('items').where('category_id', '==', cat_id).stream()
    for item in items:
        db.collection('items').document(item.id).update({'category_id': None})

# --- عمليات الأصناف (Items) ---
def add_item(name, description, images, videos, pdf, price, discount, specs, category_id, keywords):
    db.collection('items').add({
        'name': name,
        'description': description,
        'images': images,  # ستبقى مسارات محلية بناءً على طلبك
        'videos': videos,
        'pdf': pdf,
        'price': price,
        'discount': discount,
        'specs': specs,
        'category_id': category_id,
        'keywords': keywords
    })

def get_all_items():
    docs = db.collection('items').stream()
    items = []
    # نحتاج لجلب أسماء الفئات أيضاً
    categories = {c['id']: c['name'] for c in get_all_categories()}
    
    for doc in docs:
        data = doc.to_dict()
        item = {'id': doc.id, **data}
        item['category_name'] = categories.get(data.get('category_id'), 'بدون فئة')
        # التأكد من أن القوائم موجودة (لأن Firestore لا يحتاج json.loads)
        item['images'] = item.get('images', [])
        item['videos'] = item.get('videos', [])
        item['specs'] = item.get('specs', {})
        items.append(item)
    return items

def get_items_by_category(category_id):
    docs = db.collection('items').where('category_id', '==', category_id).stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        item = {'id': doc.id, **data}
        item['images'] = item.get('images', [])
        item['videos'] = item.get('videos', [])
        item['specs'] = item.get('specs', {})
        items.append(item)
    return items

def get_item_by_id(item_id):
    doc = db.collection('items').document(item_id).get()
    if doc.exists:
        data = doc.to_dict()
        item = {'id': doc.id, **data}
        item['images'] = item.get('images', [])
        item['videos'] = item.get('videos', [])
        item['specs'] = item.get('specs', {})
        return item
    return None

def update_item(item_id, name, description, price, discount, specs, category_id, keywords):
    db.collection('items').document(item_id).update({
        'name': name,
        'description': description,
        'price': price,
        'discount': discount,
        'specs': specs,
        'category_id': category_id,
        'keywords': keywords
    })

def delete_item(item_id):
    item = get_item_by_id(item_id)
    if item:
        # حذف الملفات المحلية إذا كانت موجودة (لن تعمل على Railway بين الحاويات)
        all_files = item['images'] + item['videos'] + ([item['pdf']] if item['pdf'] else [])
        for f in all_files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
        db.collection('items').document(item_id).delete()

# --- عمليات الأوراق ---
def add_document(name, file_path, keywords):
    db.collection('documents').add({
        'name': name,
        'file_path': file_path,
        'keywords': keywords
    })

def get_all_documents():
    docs = db.collection('documents').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def delete_document(doc_id):
    doc = get_document_by_id(doc_id)
    if doc:
        if os.path.exists(doc['file_path']):
            try: os.remove(doc['file_path'])
            except: pass
        db.collection('documents').document(doc_id).delete()

def get_document_by_id(doc_id):
    doc = db.collection('documents').document(doc_id).get()
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None
