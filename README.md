# SmartExam 📝

A full-stack, VSTEP-aligned English proficiency exam platform built with **Django REST Framework**, **Celery**, and a vanilla JS frontend. SmartExam supports the full exam lifecycle — from exam creation and timed delivery to AI-assisted grading and expert review.

---

## ✨ Features

- **VSTEP-Aligned Exam Structure** — Exams are organized into 4 sections: Listening, Reading, Writing, and Speaking, each with configurable parts, questions, and time limits.
- **Multiple Question Types** — MCQ, True/False/Not Given, Matching, Long-form Writing, and Audio Recording.
- **Timed Section Management** — Per-section timers with time-spent tracking per candidate.
- **Async AI Grading (Celery + Gemini)** — Writing responses are automatically queued and graded by Google Gemini AI, producing per-criterion scores (Task Fulfillment, Coherence, Vocabulary, Grammar) and detailed feedback.
- **Role-Based Access Control (RBAC)** — Three roles with distinct permissions:
  - `ADMIN` (Board of Education) — Full system access, user management.
  - `EXAMINER` (Expert) — Reviews AI-graded submissions, accesses anonymized responses, views AI feedback.
  - `TEACHER` (Candidate) — Takes exams, views own results and score breakdown.
- **JWT Authentication** — Secure token-based authentication via `djangorestframework-simplejwt`.
- **Autosave Responses** — Upsert-based API ensures candidate answers are continuously auto-saved without data loss.
- **Detailed Score Breakdown** — Scores are tracked at the section level and aggregated into a consolidated exam score.
- **Dockerized Deployment** — Production-ready setup with Docker Compose, Nginx, Gunicorn, PostgreSQL, and Redis.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                     Nginx (Port 80)                  │
│         (Reverse proxy + static/media files)         │
└─────────────┬───────────────────────────────────────┘
              │
    ┌─────────▼─────────┐
    │  Django / Gunicorn │  ← REST API (JWT Auth, RBAC)
    │     (Port 8000)    │
    └──────┬────────┬───┘
           │        │
    ┌──────▼──┐  ┌──▼──────────────┐
    │PostgreSQL│  │  Celery Worker  │  ← Async AI Grading
    │  (DB)   │  │  (Redis Broker) │
    └─────────┘  └────────┬────────┘
                          │
                  ┌───────▼────────┐
                  │  Gemini AI API │  ← Writing Evaluation
                  └────────────────┘
```

**Frontend:** Vanilla HTML/CSS/JS (`frontend/`) served via Nginx.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 5.0 + Django REST Framework |
| Authentication | JWT (`djangorestframework-simplejwt`) |
| Database | PostgreSQL 15 |
| Task Queue | Celery 5.3 + Redis 7 |
| AI Grading | Google Gemini API (`gemini-2.5-flash`) |
| Web Server | Gunicorn + Nginx |
| Containerization | Docker + Docker Compose |
| Frontend | Vanilla HTML, CSS, JavaScript |

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose installed.
- A Google Gemini API key (optional — falls back to mock grading if not provided).

### 1. Clone the repository

```bash
git clone https://github.com/your-username/SmartExam.git
cd SmartExam
```

### 2. Configure environment variables

Copy the example `.env` file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
DEBUG=0
SECRET_KEY=your-strong-secret-key-here
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
DATABASE_URL=postgres://examuser:examsecretpassword@db:5432/smartexam_db
CELERY_BROKER_URL=redis://redis:6379/0
GEMINI_API_KEY=your-gemini-api-key-here   # Optional
```

> **Note:** If `GEMINI_API_KEY` is not set, the system falls back to a mock grading response for development/testing.

### 3. Build and run with Docker Compose

```bash
docker-compose up --build -d
```

This starts 5 services:
- `db` — PostgreSQL database
- `redis` — Redis message broker
- `web` — Django application (Gunicorn)
- `celery_worker` — Background task processor
- `nginx` — Reverse proxy on port 80

### 4. Initialize the database

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic --noinput
```

### 5. Access the application

| URL | Description |
|---|---|
| `http://localhost/` | Frontend (Vanilla JS app) |
| `http://localhost/api/` | REST API root |
| `http://localhost/admin/` | Django Admin Panel |

---

## 📁 Project Structure

```
SmartExam/
├── smartexam/
│   ├── core/
│   │   ├── models.py          # Data models (User, Exam, Section, Question, Submission, etc.)
│   │   ├── views.py           # API ViewSets and endpoints
│   │   ├── serializers.py     # DRF serializers
│   │   ├── services.py        # Business logic (section scoring, exam completion)
│   │   ├── tasks.py           # Celery tasks (AI grading pipeline)
│   │   ├── permissions.py     # Custom DRF permission classes (RBAC)
│   │   ├── decorators.py      # Role-based view decorators
│   │   ├── mixins.py          # Reusable view mixins
│   │   ├── admin.py           # Django Admin configuration
│   │   └── urls.py            # API routing
│   ├── settings.py
│   ├── celery.py
│   └── urls.py
├── frontend/
│   ├── index.html             # Single-page frontend
│   ├── app.js                 # Exam delivery logic (timers, autosave, audio recording)
│   └── style.css
├── nginx/
│   └── nginx.conf
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🔌 API Endpoints

All endpoints require JWT authentication (`Authorization: Bearer <token>`).

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/token/` | Obtain JWT token pair |
| `POST` | `/api/token/refresh/` | Refresh access token |
| `GET` | `/api/exams/` | List all published exams |
| `GET` | `/api/exams/{id}/` | Retrieve full exam structure |
| `POST` | `/api/submissions/` | Start a new exam attempt |
| `POST` | `/api/submissions/{id}/start_section/` | Begin a section timer |
| `POST` | `/api/submissions/{id}/finish_exam/` | Finalize exam and queue grading |
| `POST` | `/api/section-submissions/{id}/complete/` | Submit a completed section |
| `POST` | `/api/responses/` | Save/autosave a question response |
| `GET` | `/api/get-ai-feedback/{id}/` | Retrieve AI evaluation for a response *(Examiner only)* |

---

## 🤖 AI Grading Pipeline

When a **Writing** section is submitted:

1. The section is finalized via `/api/section-submissions/{id}/complete/`.
2. A Celery task (`process_subjective_grading`) is dispatched.
3. Each `TEXT_LONG` response is queued for the `grade_vstep_writing_with_ai` task.
4. The Gemini AI API evaluates the essay and returns structured JSON scores:
   - **Task Fulfillment** (0–10)
   - **Coherence** (0–10)
   - **Vocabulary** (0–10)
   - **Grammar** (0–10)
   - **General Summary** and **Grammar/Vocabulary Errors**
5. The response status is updated to `READY_FOR_GRADING` for Examiner review.

For **Speaking** responses, audio metadata is processed and flagged for expert review.

---

## 👥 User Roles

| Role | Description | Key Permissions |
|---|---|---|
| `ADMIN` | Board of Education | Full access, user management, all submissions |
| `EXAMINER` | Expert Grader | View all submissions (anonymized), access AI feedback, grade Writing/Speaking |
| `TEACHER` | Candidate | Take exams, view own results and score breakdown |

Superusers are automatically assigned the `ADMIN` role.

---

## 🧪 Development Utilities

```bash
# Test the AI grading pipeline manually
python test_grading.py

# Verify your Gemini API key is working
python test_openai_key.py

# Fix any inconsistent exam data
python fix_exams.py
```

---

## 📄 License

This project is for educational and portfolio purposes.
