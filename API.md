# API Documentation — Smart Life Organizer

This document describes the server-side AJAX/API endpoints exposed by the `planner` app. All endpoints under `/api/` require an authenticated user (login session/cookie). Some additional endpoints exist for exports and imports.

Base URL: `/` (assumes Django is served at the root).

Auth: All `/api/` endpoints require authentication. Use the normal login flow (`/login/`) or session cookies from the web UI. CSRF tokens are required for POST requests when called from browsers.

Contents
- Events
- Categories
- Habits
- Tasks
- Pomodoro
- Import / Export
- Notes

---

Events
------

- GET `/api/events/feed/?start=...&end=...`
  - Description: Returns events (including expanded recurring occurrences) in a FullCalendar-compatible JSON array.
  - Method: GET
  - Query params:
    - `start` (ISO date or datetime) — calendar start range (FullCalendar supplies this)
    - `end` (ISO date or datetime) — calendar end range
  - Response: Array of event objects with fields like `id`, `title`, `start`, `end`, `color`, `textColor`, and `extendedProps` (category, description, isRecurring, originalStart, isCompleted, or isTask for tasks).

- POST `/api/events/create/`
  - Description: Create a new event (supports simple recurrence fields).
  - Method: POST (JSON body)
  - Request body example:
    ```json
    {
      "title": "Team sync",
      "description": "Weekly status",
      "start_time": "2026-05-13T09:00",
      "end_time": "2026-05-13T10:00",
      "category": "Work",
      "category_color": "#0d9488",
      "rrule": "FREQ=WEEKLY;BYDAY=WE",        
      "recurrence_end": "2026-12-31T23:59:59"
    }
    ```
  - Response success (201):
    ```json
    {
      "success": true,
      "id": 123,
      "title": "Team sync",
      "start_time": "2026-05-13T09:00:00+00:00",
      "end_time": "2026-05-13T10:00:00+00:00",
      "category": "Work",
      "category_color": "#0d9488",
      "category_created": false
    }
    ```
  - Errors: 400 for missing/invalid fields (e.g., missing title, invalid datetimes).

- POST `/api/events/<event_id>/edit/`
  - Description: Edit a series or a single occurrence of a recurring event.
  - Method: POST (JSON body)
  - Body fields: same as create plus:
    - `scope`: "series" (default) or "single"
    - `original_start`: ISO datetime of the occurrence when `scope` is `single`.
  - Response: `{"success": true, "updated_occurrence": true|false}`

- POST `/api/events/<event_id>/delete/`
  - Description: Delete a whole event/series or cancel a single recurring occurrence.
  - Method: POST (JSON body)
  - Body example for single occurrence deletion:
    ```json
    { "scope": "single", "original_start": "2026-05-20T09:00:00" }
    ```
  - Response: `{"success": true, "deleted_occurrence": true|false}`

Categories
----------

- POST `/api/categories/<cat_id>/edit/`
  - Description: Edit a category's name and color.
  - Method: POST (JSON body)
  - Body example: `{ "name": "Personal", "color": "#ef4444" }`
  - Response: `{"success": true, "name": "Personal", "color": "#ef4444"}`

- POST `/api/categories/<cat_id>/delete/`
  - Description: Delete a category (Django cascade will remove associated events if configured).
  - Method: POST
  - Response: `{"success": true}` or error if not found.

Habits
------

- POST `/api/habits/create/`
  - Description: Create a habit by name.
  - Method: POST (JSON body)
  - Body example: `{ "name": "Drink water" }`
  - Response success (201 if created): `{ "success": true, "id": 5, "name": "Drink water", "current_streak": 0, "last_completed_date": null, "created": true }`

- POST `/api/habits/<habit_id>/toggle/`
  - Description: Mark today's completion for habit (idempotent for same-day toggles).
  - Method: POST
  - Response: `{"success": true, "new_streak": 3, "last_completed": "2026-05-13", "already_done": false}`

- POST `/api/habits/<habit_id>/delete/`
  - Description: Delete a habit.
  - Method: POST
  - Response: `{"success": true}`

Tasks
-----

- POST `/api/tasks/create/`
  - Description: Create a task; optional `due_date` can be provided (ISO date or datetime).
  - Method: POST (JSON body)
  - Body example: `{ "title": "Write report", "due_date": "2026-05-14" }`
  - Response: `{"success": true, "id": 12, "title": "Write report", "is_completed": false, "due_date": "2026-05-14T00:00:00+00:00"}`

- POST `/api/tasks/<task_id>/toggle/`
  - Description: Toggle task completion state.
  - Method: POST
  - Response: `{"success": true, "is_completed": true}`

- POST `/api/tasks/<task_id>/delete/`
  - Description: Delete a task.
  - Method: POST
  - Response: `{"success": true}`

Pomodoro
--------

- POST `/api/pomodoro/complete/`
  - Description: Record a completed Pomodoro session (defaults to 25 minutes).
  - Method: POST
  - Response: `{"success": true}`

Import / Export
---------------

- GET `/export/csv/`
  - Description: Download a CSV export of the user's events and habits.
  - Method: GET
  - Response: `text/csv` attachment.

- GET `/export/ics/`
  - Description: Download an iCalendar (`.ics`) of user's events.
  - Method: GET
  - Response: `text/calendar` attachment.

- GET or POST `/import/`
  - Description: GET renders an upload form. POST accepts uploaded `.csv` or `.ics` files and imports events/habits.
  - Method: POST (multipart form upload)
  - Response JSON: `{"success": true, "created": N}`

Notes & Implementation Details
------------------------------
- Authentication: Endpoints use Django session authentication and the `@login_required` decorator.
- CSRF: Browser POST requests must include a CSRF token (forms or AJAX headers).
- Date parsing: Endpoints accept ISO date strings and HTML `datetime-local` formats; timezone-aware datetimes are used when possible.
- Recurrence: The `rrule` field is accepted as a raw RRULE string (e.g., `FREQ=DAILY;INTERVAL=1`). The app expands recurrences server-side for calendar feeds and supports single-occurrence edits/deletions via an `EventException` model.
- Status codes: 200 for OK, 201 for created resources, 400 for validation errors, 404 for not found.

Examples (curl)
---------------

Create event (authenticated session cookie required):

```bash
curl -X POST "http://localhost:8000/api/events/create/" \
  -H "Content-Type: application/json" \
  -b "sessionid=..." \
  -d '{"title":"Meeting","start_time":"2026-05-13T09:00","end_time":"2026-05-13T10:00","category":"Work"}'
```

Fetch calendar feed (FullCalendar):

```bash
curl "http://localhost:8000/api/events/feed/?start=2026-05-01&end=2026-05-31" -b "sessionid=..."
```

---

If you'd like, I can:
- Add OpenAPI/Swagger JSON for these endpoints.
- Include example Postman collection or ready-to-run curl scripts.
- Add authentication notes for token-based access (if you plan to support API tokens later).
