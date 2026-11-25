# 📚 Student Library Management System

A full-featured web-based library management platform built with **Flask**, **SQLAlchemy**, and **Bootstrap 5**. Designed for universities and colleges to streamline book catalogue browsing, member management, circulation workflows, due-date tracking, automated fine calculations, and audit logging.

---

## ✨ Features

- **Role-Based Access Control**:
  - **Admin**: Full system management, user status/role configuration, catalogue additions/modifications, system parameters, audit logs, and circulation analytics.
  - **Librarian**: Circulation desk operations (issue, return with barcode/accession scanning), borrow requests review, overdue tracking, physical inventory status.
  - **Student**: Online catalogue search with category filters, borrow requests, real-time tracking of active loans and due dates, fine status, and notifications.
- **Automated Fine Calculation**: Auto-assesses daily penalties for overdue returns with fee payment/waiver workflows.
- **Audit Logging**: Comprehensive activity tracking for administrative transparency and security.
- **Responsive UI**: Clean design system built with Bootstrap 5, Bootstrap Icons, and Chart.js.

---

## 🚀 Quick Local Setup

### 1. Clone or Open the Repository
```bash
git clone https://github.com/<your-username>/student_library_management.git
cd student_library_management
```

### 2. Set Up a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```env
FLASK_ENV=development
SECRET_KEY=change-this-to-a-secure-random-key
DATABASE_URL=sqlite:///student_library.db
UPLOAD_FOLDER=app/static/uploads
MAX_CONTENT_LENGTH_MB=5
SESSION_COOKIE_SECURE=false
```

### 5. Initialize Database & Seed Demo Data
```bash
flask init-db
flask seed-demo --password Pass1234
```

### 6. Run the Application
```bash
python run.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🔑 Demo Accounts

| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@library.edu` | `Pass1234` |
| **Librarian** | `librarian@library.edu` | `Pass1234` |
| **Student** | `alice@student.edu` | `Pass1234` |

---

## 🌐 Deploying to the Cloud via GitHub

> **Note**: **GitHub Pages** only hosts static websites (HTML/CSS/JS). Because this is a dynamic Python/Flask application with a database and backend routing, it needs a cloud runtime like **Render**, **Railway**, or **PythonAnywhere**.

### Step 1: Push Project to GitHub
```bash
git init
git add .
git commit -m "Initial commit of Student Library Management System"
git branch -M main
git remote add origin https://github.com/<your-username>/student-library-management.git
git push -u origin main
```

### Step 2: Deploy to Render (Free)
1. Go to [Render.com](https://render.com) and sign in with GitHub.
2. Click **New +** -> **Web Service**.
3. Select your repository `student-library-management`.
4. Configure service settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app`
5. Add Environment Variables in Render dashboard:
   - `SECRET_KEY`: `<generate-random-secret>`
   - `FLASK_ENV`: `production`
   - `DATABASE_URL`: `sqlite:///student_library.db` (or a managed PostgreSQL/MySQL database)
   - `SESSION_COOKIE_SECURE`: `true`
6. Click **Deploy Web Service** — Render gives you a public `.onrender.com` URL accessible by anyone!

