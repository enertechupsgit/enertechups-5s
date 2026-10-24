# Enertech 5S - Enterprise 5S Management System

An industrial-grade 5S Activity Management, Before/After Evidence Tracking, and Plant Zone Auditing Platform built for **EnerTech UPS Pvt. Ltd.**

---

## 🏗️ Architecture & Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Recharts
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy (Async), SQLite / PostgreSQL
- **Key Modules**:
  - **Work Orders**: 5S Pillar tracking (`1S Sort`, `2S Set in Order`, `3S Shine`, `4S Standardize`, `5S Sustain`)
  - **Asset Management**: Complete equipment registry, status & reliability tracking, sub-component hierarchies
  - **Team & Leaders**: Zonal leader assignments, supervisory roles, and plant area management
  - **Red Tagging**: Non-conformance tagging, item categorization, and disposition management
  - **Audits & Scoring**: Multi-point 5S audit checklists, automated radar chart scoring, and compliance reports

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js** v18+ and **npm**
- **Python** 3.10+

---

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend development server (runs on http://127.0.0.1:8000)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

### 3. Frontend Setup

```bash
cd apps/web

# Install dependencies (the current UI uses pnpm and Tailwind CSS 4)
pnpm install

# Run frontend development server (runs on http://127.0.0.1:5173)
pnpm run dev
```

Build for production:
```bash
pnpm run build
```

---

## 🏭 Organization & Plant Configuration
- **Company**: EnerTech UPS Pvt. Ltd.
- **Facility**: EnerTech UPS - Unit 1 (ET-01)
- **Role**: Plant Management & Operations Oversight

## Render deployment

Deploy frontend and backend together using the root `render.yaml` Blueprint and `Dockerfile`. See [the Render deployment guide](docs/RENDER-DEPLOYMENT.md) for PostgreSQL provisioning and first-administrator setup. Local sample role switching is disabled online.
