import os
import json
import re
import base64
import logging
import firebase_admin
from firebase_admin import credentials, firestore

# إعداد الـ Logging لمراقبة الاتصال في Railway
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_db = None

def get_db():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            init_firebase()
        _db = firestore.client()
    return _db

def init_firebase():
    """
    تهيئة Firebase باستخدام أفضل الممارسات لبيئات الـ Cloud.
    الأولوية: Base64 -> JSON Env -> Local File
    """
    cred = None
    
    try:
        # 1. الأولوية الأولى: Base64 (الحل الأضمن)
        base64_config = os.getenv('FIREBASE_CONFIG_BASE64')
        if base64_config:
            logger.info("Attempting to initialize Firebase using Base64 config...")
            decoded_config = base64.b64decode(base64_config).decode('utf-8')
            cred_dict = json.loads(decoded_config)
            cred = _create_credential_from_dict(cred_dict)

        # 2. الأولوية الثانية: JSON Raw Env
        if not cred:
            raw_json_config = os.getenv('FIREBASE_CONFIG')
            if raw_json_config:
                logger.info("Attempting to initialize Firebase using JSON Raw config...")
                cred_dict = json.loads(raw_json_config)
                cred = _create_credential_from_dict(cred_dict)

        # 3. الأولوية الثالثة: ملف محلي (للتطوير المحلي فقط)
        if not cred:
            cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'firebase_key.json')
            if os.path.exists(cred_path):
                logger.info("Attempting to initialize Firebase using local firebase_key.json...")
                cred = credentials.Certificate(cred_path)

        if cred:
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized successfully.")
        else:
            logger.error("❌ Failed to find Firebase credentials in any source!")
            raise Exception("No Firebase credentials found!")

    except Exception as e:
        logger.error(f"💥 Critical error initializing Firebase: {str(e)}")
        raise e

def _create_credential_from_dict(cred_dict):
    """مساعد لإصلاح الـ private_key وإنشاء الـ Certificate"""
    if 'private_key' in cred_dict:
        # إصلاح مشكلة الـ newline التي تسبب Invalid JWT Signature
        cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')
    return credentials.Certificate(cred_dict)

def init_db():
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
    get_db().collection('categories').add({
        'name': name,
        'keywords': keywords
    })

def get_all_categories():
    docs = get_db().collection('categories').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def delete_category(cat_id):
    get_db().collection('categories').document(cat_id).delete()
    # تحديث الأصناف التي تتبع هذه الفئة
    items = get_db().collection('items').where('category_id', '==', cat_id).stream()
    for item in items:
        get_db().collection('items').document(item.id).update({'category_id': None})

# --- عمليات الأصناف (Items) ---
def add_item(name, description, images, videos, pdf, price, discount, specs, category_id, keywords):
    get_db().collection('items').add({
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
    docs = get_db().collection('items').stream()
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
    docs = get_db().collection('items').where('category_id', '==', category_id).stream()
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
    doc = get_db().collection('items').document(item_id).get()
    if doc.exists:
        data = doc.to_dict()
        item = {'id': doc.id, **data}
        item['images'] = item.get('images', [])
        item['videos'] = item.get('videos', [])
        item['specs'] = item.get('specs', {})
        return item
    return None

def update_item(item_id, name, description, price, discount, specs, category_id, keywords):
    get_db().collection('items').document(item_id).update({
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
        get_db().collection('items').document(item_id).delete()

# --- عمليات الأوراق ---
def add_document(name, file_path, keywords):
    get_db().collection('documents').add({
        'name': name,
        'file_path': file_path,
        'keywords': keywords
    })

def get_all_documents():
    docs = get_db().collection('documents').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def delete_document(doc_id):
    doc = get_document_by_id(doc_id)
    if doc:
        if os.path.exists(doc['file_path']):
            try: os.remove(doc['file_path'])
            except: pass
        get_db().collection('documents').document(doc_id).delete()

def get_document_by_id(doc_id):
    doc = get_db().collection('documents').document(doc_id).get()
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None
