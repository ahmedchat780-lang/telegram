import re
from firebase_config import db, bucket
from google.cloud import firestore

def normalize_arabic(text):
    if not text:
        return ""
    # Remove Tashkeel
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # Unify Alef
    text = re.sub(r'[أإآ]', 'ا', text)
    # Unify Yeh
    text = re.sub(r'ى', 'ي', text)
    # Unify Teh Marbuta
    text = re.sub(r'ة', 'ه', text)
    return text.strip().lower()

# --- Category Operations ---
def get_categories():
    docs = db.collection('categories').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def add_category(name):
    db.collection('categories').add({'name': name})

def delete_category(category_id):
    db.collection('categories').document(category_id).delete()

# --- Item Operations ---
def get_items():
    docs = db.collection('items').stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def get_item_by_id(item_id):
    doc = db.collection('items').document(item_id).get()
    return {'id': doc.id, **doc.to_dict()} if doc.exists else None

def add_item(name, description, category_id, keywords, file_obj=None):
    file_url = ""
    if file_obj:
        blob = bucket.blob(f"items/{file_obj.filename}")
        blob.upload_from_file(file_obj)
        blob.make_public()
        file_url = blob.public_url

    item_data = {
        'name': name,
        'description': description,
        'category_id': category_id,
        'keywords': [normalize_arabic(k.strip()) for k in keywords.split(',')],
        'file_url': file_url,
        'normalized_name': normalize_arabic(name)
    }
    db.collection('items').add(item_data)

def update_item(item_id, name, description, category_id, keywords):
    item_ref = db.collection('items').document(item_id)
    item_data = {
        'name': name,
        'description': description,
        'category_id': category_id,
        'keywords': [normalize_arabic(k.strip()) for k in keywords.split(',')],
        'normalized_name': normalize_arabic(name)
    }
    item_ref.update(item_data)

def delete_item(item_id):
    # Optionally delete file from storage too
    item = get_item_by_id(item_id)
    if item and item.get('file_url'):
        try:
            # Extract filename from URL or store blob path in DB (better)
            filename = item['file_url'].split('/')[-1].split('?')[0]
            blob = bucket.blob(f"items/{filename}")
            if blob.exists():
                blob.delete()
        except:
            pass
    db.collection('items').document(item_id).delete()

# --- Search Logic ---
def search_items(query):
    query_norm = normalize_arabic(query)
    all_items = get_items()
    results = []
    
    for item in all_items:
        # Match name or keywords
        if query_norm in item.get('normalized_name', '') or \
           any(query_norm in k for k in item.get('keywords', [])):
            results.append(item)
            
    return results

def get_items_by_category(category_id):
    docs = db.collection('items').where('category_id', '==', category_id).stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]
