import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from fuzzywuzzy import process
from database import (
    get_all_items, get_item_by_id, get_items_by_category,
    get_all_documents, get_document_by_id,
    get_all_categories,
    normalize_arabic
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.getenv('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛍️ المنتجات والأصناف", callback_data='menu_cats')],
        [InlineKeyboardButton("📄 الأوراق الرسمية", callback_data='menu_docs')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "مرحباً بك في بوت الشركة! 👋\nيرجى اختيار القسم المطلوب:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = normalize_arabic(update.message.text)
    
    # 1. البحث في الأصناف (Items)
    items = get_all_items()
    item_choices = {}
    for i in items:
        item_choices[normalize_arabic(i['name'])] = i['id']
        if i.get('keywords'):
            for kw in i['keywords'].split(','):
                item_choices[normalize_arabic(kw.strip())] = i['id']
                
    best_item = process.extractOne(user_text, item_choices.keys(), score_cutoff=75)

    if best_item:
        item = get_item_by_id(item_choices[best_item[0]])
        await send_item_details(update, context, item)
        return

    # 2. البحث في الفئات (Categories)
    categories = get_all_categories()
    cat_choices = {}
    for c in categories:
        cat_choices[normalize_arabic(c['name'])] = c['id']
        if c.get('keywords'):
            for kw in c['keywords'].split(','):
                cat_choices[normalize_arabic(kw.strip())] = c['id']
                
    best_cat = process.extractOne(user_text, cat_choices.keys(), score_cutoff=75)
    
    if best_cat:
        cat_id = cat_choices[best_cat[0]]
        from database import get_items_by_category
        items = get_items_by_category(cat_id)
        if items:
            keyboard = [[InlineKeyboardButton(i['name'], callback_data=f"itm_{i['id']}")] for i in items]
            await update.message.reply_text(f"إليك المنتجات في فئة {best_cat[0]}:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("هذه الفئة فارغة حالياً.")
        return

    # 3. البحث في الأوراق (Documents)
    docs = get_all_documents()
    doc_choices = {}
    for d in docs:
        doc_choices[normalize_arabic(d['name'])] = d['id']
        if d['keywords']:
            for kw in d['keywords'].split(','):
                doc_choices[normalize_arabic(kw.strip())] = d['id']
    
    best_doc = process.extractOne(user_text, doc_choices.keys(), score_cutoff=75)
    
    if best_doc:
        doc = get_document_by_id(doc_choices[best_doc[0]])
        await send_document_file(update, context, doc)
        return

    await update.message.reply_text("عذراً، لم أجد نتائج مطابقة لبحثك. حاول استخدام كلمات أخرى أو اختر من القائمة /start")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'menu_cats':
        categories = get_all_categories()
        if not categories:
            await query.edit_message_text("لا توجد فئات حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data='back_main')]]))
            return
        keyboard = [[InlineKeyboardButton(cat['name'], callback_data=f"list_cat_{cat['id']}")] for cat in categories]
        keyboard.append([InlineKeyboardButton("🔙 العودة للرئيسية", callback_data='back_main')])
        await query.edit_message_text("اختر الفئة التابعة لها المنتجات:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('list_cat_'):
        cat_id = query.data.split('_')[2]
        items = get_items_by_category(cat_id)
        if not items:
            await query.edit_message_text("لا توجد منتجات في هذه الفئة حالياً.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة للفئات", callback_data='menu_cats')]]))
            return
        keyboard = [[InlineKeyboardButton(i['name'], callback_data=f"itm_{i['id']}")] for i in items]
        keyboard.append([InlineKeyboardButton("🔙 عودة للفئات", callback_data='menu_cats')])
        await query.edit_message_text("المنتجات المتاحة في هذه الفئة:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif query.data == 'menu_docs':
        docs = get_all_documents()
        keyboard = [[InlineKeyboardButton(d['name'], callback_data=f"doc_{d['id']}")] for d in docs]
        keyboard.append([InlineKeyboardButton("🔙 العودة للرئيسية", callback_data='back_main')])
        await query.edit_message_text("قائمة الأوراق الرسمية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'back_main':
        await start(update, context)

    elif query.data.startswith('itm_'):
        item_id = query.data.split('_')[1]
        item = get_item_by_id(item_id)
        if item: await send_item_details(update, context, item)

    elif query.data.startswith('doc_'):
        doc_id = query.data.split('_')[1]
        doc = get_document_by_id(doc_id)
        if doc: await send_document_file(update, context, doc)

async def send_item_details(update, context, item):
    chat_id = update.effective_chat.id
    caption = f"📦 *{item['name']}*\n"
    if item['description']: caption += f"📝 {item['description']}\n"
    if item['price']: caption += f"💰 السعر: {item['price']}\n"
    if item['specs']:
        caption += "\n📋 *المواصفات:*\n"
        for k, v in item['specs'].items(): caption += f"- {k}: {v}\n"

    media = []
    for img in item['images']:
        if os.path.exists(img): media.append(InputMediaPhoto(open(img, 'rb')))
    for vid in item['videos']:
        if os.path.exists(vid): media.append(InputMediaVideo(open(vid, 'rb')))

    if media:
        media[0].caption = caption
        media[0].parse_mode = 'Markdown'
        await context.bot.send_media_group(chat_id=chat_id, media=media)
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode='Markdown')

async def send_document_file(update, context, doc):
    chat_id = update.effective_chat.id
    file_path = doc['file_path']
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            ext = file_path.lower().split('.')[-1]
            if ext in ['jpg', 'jpeg', 'png']:
                await context.bot.send_photo(chat_id=chat_id, photo=f, caption=f"📄 ورقة: {doc['name']}")
            else:
                await context.bot.send_document(chat_id=chat_id, document=f, caption=f"📄 ورقة: {doc['name']}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Bot is running with Categories and Items support...")
    application.run_polling()
