# Smart Life Organizer

A comprehensive Django-based application designed to help organize your life efficiently. It features task planning, user management, and AI engine integrations.

## Features
- **Planner**: Manage tasks, events, and categories.
- **AI Engine**: Intelligent features and services.
- **User Management**: Authentication, profiles, and customizable settings.

## Getting Started

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd Smart-Life-Organizer
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Apply database migrations:
   ```bash
   python manage.py migrate
   ```

5. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Structure
- `planner/`: App for scheduling and organizing events.
- `ai_engine/`: App containing AI-driven capabilities.
- `users/`: App handling user accounts and profiles.
- `smartlife_project/`: Main Django project configuration.
