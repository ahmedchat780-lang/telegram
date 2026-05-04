# 🔥 Enterprise Telegram Bot (Firebase Edition)

A scalable, cloud-native Telegram bot system with a Firebase backend and a premium Admin Panel.

## 🚀 Features
- **Cloud Database**: Firestore for real-time data management.
- **Cloud Storage**: Firebase Storage for images and PDF documents.
- **Arabic Smart Matching**: Normalized search for Arabic text (handles typos and character variations).
- **Categorized Browsing**: Users can browse items by category via inline keyboards.
- **Production Ready**: Supports Webhooks for efficient deployment on Render.

## 🛠️ Firebase Setup (Essential)

1.  **Create a Firebase Project**: Go to [Firebase Console](https://console.firebase.google.com/).
2.  **Enable Firestore**: Create a database in "Production Mode" or "Test Mode".
3.  **Enable Storage**: Initialize Firebase Storage.
4.  **Service Account**:
    - Go to **Project Settings** > **Service Accounts**.
    - Click **Generate New Private Key**.
    - Rename the downloaded JSON file to `firebase-service-account.json` and place it in the project root.
5.  **Storage Bucket**: Copy your bucket name (e.g., `your-project.appspot.com`) and add it to `.env`.

## 💻 Local Development

1.  **Install dependencies**:
    ```bash
    py -m pip install -r requirements.txt
    ```
2.  **Configure `.env`**: Add your `BOT_TOKEN` and Firebase details.
3.  **Run Admin Panel**: `py app.py` (Visit `http://localhost:5000`)
4.  **Run Bot**: `py bot.py`

## ☁️ Deployment (Render)

### 1. Environment Variables
Add these to Render's environment settings:
- `BOT_TOKEN`: From @BotFather.
- `FIREBASE_CREDENTIALS`: Paste the **entire content** of your service account JSON file here.
- `FIREBASE_STORAGE_BUCKET`: Your appspot URL.
- `RENDER_EXTERNAL_URL`: Your Render service URL (e.g., `https://my-bot.onrender.com`).
- `SECRET_KEY`: Any random string.

### 2. Services
- **Web Service**: Runs the Admin Panel (`gunicorn app:app`).
- **Worker/Web Service**: Runs the Bot (`python bot.py`). 
  *Note: Since the bot uses Webhooks, it should technically be part of the Flask app or a separate service that Render can reach.*

## 📁 Project Structure
- `services/firestore_service.py`: Core logic for DB and search.
- `firebase_config.py`: Firebase initialization.
- `bot.py`: Telegram bot with Webhook/Polling support.
- `app.py`: Flask Admin Panel.
