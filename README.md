# Smart Life Organizer

A personal productivity and life-organizing web app built with Django. Provides calendar, tasks, reminders, pomodoro sessions, habit tracking, and user account features.

---

## Key Features
- **Calendar & Events:** Create, view, and manage events with recurrence rules and exceptions.
- **Tasks & To‑dos:** Task creation, due dates, categories, and Pomodoro session support.
- **Reminders:** Background scheduled reminders via Celery and Django management commands.
- **User Accounts:** Registration, email activation, password reset flows, and user profile settings.
- **Analytics & Growth Views:** Personal productivity analytics and habit growth tracking.

---

## Tech Stack
- **Framework:** Django
- **Background Worker:** Celery (configured in `smartlife_project/celery.py`)
- **DB:** SQLite (development) — `db.sqlite3` in repo root
- **Frontend:** Django templates + minimal JS (`static/js/calendar_app.js`)

---

## Prerequisites
- Python 3.8+ (use `py -3` on Windows if needed)
- virtualenv or venv

(AI / Gemini)
- `google-genai` SDK is listed in `requirements.txt`. Set `GEMINI_API_KEY` or
	`GOOGLE_APPLICATION_CREDENTIALS` for server-side AI features (see `.env.example`).

---

## Quick Start (Development)
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Apply migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
```

4. Run the development server:

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

---

## Running Celery (Reminders & Background Tasks)
This project includes Celery for background tasks and scheduled reminders. Start a worker and (optionally) a beat scheduler in development:

```bash
# From project root
celery -A smartlife_project worker --loglevel=info
# If using beat for periodic tasks:
celery -A smartlife_project beat --loglevel=info
```

Notes:
- Ensure your broker (e.g., Redis or RabbitMQ) is running and configured in `smartlife_project/settings.py`.
- For lightweight local testing you can configure an in-memory broker or use Redis.

---

## Scheduled Reminders (Management Command)
There is a management command to run reminders (see `planner/management/commands/run_reminders.py`). To execute:

```bash
python manage.py run_reminders
```

This is useful for testing reminders without Celery.

---

## Tests
Run tests with pytest (project includes `pytest.ini`):

```bash
pytest
```

Focus areas with tests are `ai_engine/tests.py`, `planner/tests.py`, and `users/tests.py`.

---

## Project Structure (high level)
- `manage.py` – Django management entrypoint.
- `smartlife_project/` – Django project settings, ASGI/WGI, and Celery config.
- `planner/` – Core app: models, views, tasks, management commands, migrations.
- `ai_engine/` – Auxiliary app with AI-related services and utilities.
- `users/` – User/account models and auth flows.
- `static/` – JavaScript and other static assets.
- `templates/` – Django templates for the UI.

See source for more details and implementation.

---

## Configuration Notes
- Database: `db.sqlite3` is used for development; change `DATABASES` in `smartlife_project/settings.py` for production.
- Email: Update email backend in `settings.py` for activation and password resets.
- Celery: Configure `CELERY_BROKER_URL` and result backend in `settings.py`.

AI / Gemini
- The project includes a lightweight Gemini wrapper at `ai_engine/services.py`.
- To enable AI tips:
	- Install dependencies: `pip install -r requirements.txt` (includes `google-genai`).
	- Add a valid `GEMINI_API_KEY` to your environment or set `GOOGLE_APPLICATION_CREDENTIALS`.
	- Restart the Django process so the client picks up the environment.
 - The wrapper degrades gracefully if the SDK or key is missing; no runtime errors will be raised.

---

## Contributing
- Fork the repository and open a PR with a clear description of changes.
- Add tests for new features or bug fixes.
- Follow existing code style and keep changes focused.

---

## Helpful Commands
- Run server: `python manage.py runserver`
- Run migrations: `python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`
- Run tests: `pytest`
- Start Celery worker: `celery -A smartlife_project worker --loglevel=info`

---

## License & Acknowledgements
This repository does not include a license file. Add a `LICENSE` if you intend to make this project public with a chosen license.

Thanks to the original author(s) for building the project.
