<div align="center">
  <h1>🚀 Smart Life Organizer</h1>
  <p><strong>An AI-integrated productivity ecosystem designed with a modern SaaS aesthetic.</strong></p>
  
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)
  [![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](#)
  [![SQL Server](https://img.shields.io/badge/SQL_Server-CC2927?style=for-the-badge&logo=microsoft-sql-server&logoColor=white)](#)
  [![Gemini AI](https://img.shields.io/badge/Google_Gemini_API-4285F4?style=for-the-badge&logo=google&logoColor=white)](#)
  [![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](#)
</div>

<br>

## 📖 Project Vision

**Smart Life Organizer** is a comprehensive, highly interactive productivity ecosystem built by engineering students at Fırat University. The platform combines traditional task and time management features with advanced Artificial Intelligence. Wrapped in a premium, full-screen SaaS interface, it helps users optimize their workflow, track progress with rich data visualizations, and receive context-aware coaching to maximize their daily efficiency.

---

## ✨ Key Features

- 🤖 **Intelligent AI Agent:** Deep integration with the **Google Gemini API** provides contextual, data-driven insights. From personalized motivational tips during focus sessions to dynamically generated roadmaps breaking down large goals into actionable tasks and habits.
- 🌓 **Dynamic Theme System:** A meticulously engineered Light and Dark Mode system utilizing scalable CSS Variables. The UI smoothly transitions between themes, maintaining a high-density, professional aesthetic across all components, charts, and modals while persisting user preferences.
- 📊 **Advanced Analytics Dashboard:** Real-time data visualization utilizing Plotly and Chart.js. The dashboard intelligently breaks down productivity metrics, calculates focus streaks, visualizes weekly activity via heatmaps, and provides an AI-generated daily efficiency tip based on historical data.

---

## 🛠️ Technical Stack

- **Backend:** Python, Django
- **Database:** Microsoft SQL Server
- **Frontend:** Vanilla JavaScript, Semantic HTML, CSS Variables (Tailwind CSS for utility styling)
- **AI Integration:** Google Gemini API
- **Data Visualization:** Plotly, Chart.js

---

## 👥 Development Team & Contributions

This project is the result of strong technical collaboration. Below is the breakdown of the engineering team and their primary architectural contributions:

| Team Member | Role & Key Contributions |
| :--- | :--- |
| **Muhammed Hadi Kaddour** | **Core Functionality Developer**<br>Architected the core backend infrastructure. Implemented the comprehensive **Habit Tracking** system and the dynamic **Category Management** modules. |
| **Amer** | **UI/UX Architect & Data Engineer**<br>Designed the overall User Interface for a modern SaaS feel. Developed the robust **Analytics Events** data pipelines and the **Global Settings** logic. |
| **Muhammed Hatip (Al-Khatib)** | **Frontend & Feature Engineer**<br>Engineered the **Pomodoro Engine** (including the seamless Light/Dark Mode toggle) and developed the highly interactive, responsive **Calendar** module. |
| **Hatip & Amer** *(Collaboration)* | **AI Development**<br>Co-engineered the **AI Agent** features, seamlessly integrating the Gemini API to provide smart insights, roadmaps, and contextual assistance across the platform. |

---

## ⚙️ Installation & Setup

Follow these steps to run the Smart Life Organizer locally on your machine.

### Prerequisites
- Python 3.9+
- Microsoft SQL Server
- Google Gemini API Key

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/smart-life-organizer.git
cd smart-life-organizer
```

### 2. Set Up a Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory of the project and add your configurations:
```env
# Example .env configuration
SECRET_KEY=your_django_secret_key
DEBUG=True

# Database Configuration
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=1433

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key
```

### 5. Apply Database Migrations
```bash
python manage.py migrate
```

### 6. Run the Development Server
```bash
python manage.py runserver
```
Visit `http://localhost:8000` in your browser to access the application.

---
<div align="center">
  <p><i>Developed with passion by students of Fırat University.</i></p>
</div>
