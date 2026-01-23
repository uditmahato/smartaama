<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/React-18.2-61DAFB?style=for-the-badge&logo=react" alt="React">
  <img src="https://img.shields.io/badge/FastAPI-Latest-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
</p>

<h1 align="center">💗 SmartAama</h1>
<h3 align="center">Maternal Health Management Platform</h3>

<p align="center">
  <strong>AI-Assisted Maternal Risk Assessment & Referral System for Primary Healthcare Facilities</strong>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Technology Stack](#-technology-stack)
- [Architecture](#-architecture)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Clinical Design Principles](#-clinical-design-principles)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**SmartAama** is a comprehensive maternal and antenatal care management system designed specifically for Primary Health Care (PHC) facilities in Nepal. The platform maintains longitudinal maternal health records, performs AI-based risk analysis, and enables timely referrals to higher-level healthcare facilities.

> **Important**: AI in SmartAama is strictly advisory. Final clinical decisions always rest with the healthcare provider.

### Built for Nepal's Healthcare System

- 🏥 Tailored for primary health centers
- 📊 Real-time clinical data tracking
- 🔄 Seamless inter-facility referrals
- 🔒 HIPAA-compliant security standards
- 🌐 Designed for resource-limited settings

---

## ✨ Key Features

### Patient Management
- **Comprehensive Patient Records**: Auto-generated patient IDs (PAT-YYYY-NNNNN format)
- **Age-Based Registration**: Simplified demographic data capture
- **Lifestyle & Social History**: Occupation, education, marital status tracking
- **Longitudinal Data**: Complete patient timeline with immutable records

### Clinical Workflows
- **ANC Visit Tracking**: Section-wise selective updates for obstetric history
- **Event-Based Recording**: All clinical updates stored as timestamped events
- **Investigation Management**: Lab results and diagnostic data integration
- **Risk Assessment**: AI-powered clinical decision support

### Referral System
- **Smart Referrals**: Intelligent routing to appropriate care levels
- **Status Tracking**: Draft → Submitted → Received → Closed workflow
- **Inter-facility Communication**: Streamlined patient handoff
- **Complete Timeline**: Full patient history accessible at referral destination

### AI & Analytics
- **Explainable AI**: RAG-based clinical guideline grounding
- **Risk Stratification**: Evidence-based risk scoring
- **Advisory Insights**: Non-prescriptive clinical suggestions
- **Audit Trails**: Complete logging for compliance and quality assurance

---

## 🛠 Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.9+ | Core backend language |
| **FastAPI** | Latest | High-performance REST API framework |
| **SQLAlchemy** | 2.x | ORM for database operations |
| **PostgreSQL** | 14+ | Primary relational database |
| **Alembic** | Latest | Database migrations |
| **JWT** | - | Secure authentication |
| **Pydantic** | 2.x | Data validation and serialization |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.2 | UI framework |
| **TypeScript** | 5.x | Type-safe development |
| **Material-UI** | 5.0 | Component library |
| **Vite** | 5.4 | Build tool and dev server |
| **React Router** | 6.x | Client-side routing |
| **Axios** | Latest | HTTP client |

### AI/ML Stack
- **Python RAG Pipeline**: Clinical guideline-grounded reasoning
- **Vector Database**: Qdrant / Weaviate (planned)
- **LangChain**: LLM orchestration
- **OpenAI GPT-4**: Natural language processing

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Home   │  │Dashboard │  │ Patients │  │ Referrals│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (JWT Auth)
┌────────────────────────┴────────────────────────────────────┐
│                      Backend (FastAPI)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Auth   │  │ Patients │  │   ANC    │  │ Referrals│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   AI     │  │  Events  │  │   Audit  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                    PostgreSQL Database                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Patients │  │  Events  │  │ Referrals│  │   Users  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed on your system:

- **Python**: 3.9 or higher
- **Node.js**: 18.x or higher
- **npm**: 8.x or higher
- **PostgreSQL**: 14 or higher
- **Git**: Latest version

### Backend Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/smartaama.git
cd smartaama
```

#### 2. Create Virtual Environment

**Windows:**
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
```

**Linux/macOS:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Database

Create a PostgreSQL database:
```sql
CREATE DATABASE smartaama;
```

Create `.env` file in `backend/` directory:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/smartaama
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
BOOTSTRAP_TOKEN=your-bootstrap-token
```

#### 5. Run Database Migrations

```bash
alembic upgrade head
```

#### 6. Start Backend Server

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at: **http://localhost:8000**

### Frontend Setup

#### 1. Navigate to Frontend Directory

```bash
cd frontend
```

#### 2. Install Dependencies

```bash
npm install
```

#### 3. Configure Environment

Create `.env` file in `frontend/` directory:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

#### 4. Start Development Server

```bash
npm run dev
```

✅ Frontend running at: **http://localhost:5173**

---

## 📖 Usage

### First-Time Setup

1. **Access the application**: Navigate to `http://localhost:5173`
2. **Bootstrap Admin User**: Use the bootstrap token to create the first admin account
3. **Login**: Use admin credentials to access the system
4. **Add Patients**: Navigate to Dashboard → Add Patient

### User Roles

- **Admin**: Full system access, user management
- **Clinician**: Patient records, clinical data, referrals
- **Viewer**: Read-only access to patient records

---

## 📚 API Documentation

### Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login` | User authentication |
| `POST` | `/api/v1/auth/bootstrap-admin` | Create first admin user |
| `GET` | `/api/v1/auth/me` | Get current user info |
| `GET` | `/api/v1/patients` | List/search patients |
| `POST` | `/api/v1/patients` | Create new patient |
| `GET` | `/api/v1/patients/{id}` | Get patient details |
| `POST` | `/api/v1/referrals` | Create referral |
| `GET` | `/api/v1/referrals` | List referrals |

---

## 🏥 Clinical Design Principles

SmartAama follows evidence-based clinical design principles:

### Data Integrity
- ✅ **Immutable Records**: Clinical data is never deleted or overwritten
- ✅ **Event-Based Storage**: All updates stored as timestamped events
- ✅ **Complete Audit Trail**: Full history of all clinical actions
- ✅ **Version Control**: Track changes to patient records over time

### Clinical Workflows
- 📝 **Section-wise Updates**: Update only relevant clinical sections
- 🔄 **Longitudinal Tracking**: Maintain complete patient timeline
- 🎯 **Risk Stratification**: Evidence-based risk assessment
- 📤 **Seamless Referrals**: Preserve full context during transfers

### Safety & Compliance
- 🔒 **Role-Based Access**: Granular permission controls
- 🔐 **Secure Authentication**: JWT-based token system
- 📋 **HIPAA Standards**: Privacy and security compliance
- ⚠️ **AI Advisory Only**: Human clinician has final decision authority

---

## 🌐 Deployment

### Docker Deployment (Recommended)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Considerations

- Use environment-specific `.env` files
- Configure HTTPS with SSL certificates
- Set up database backups
- Configure monitoring and logging
- Implement rate limiting
- Use production-grade WSGI server (Gunicorn)

---

## 🔧 Troubleshooting

### Backend Issues

**Problem**: Backend won't start
```bash
# Verify Python version
python --version  # Should be 3.9+

# Verify virtual environment is activated
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Problem**: Database connection errors
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL in `.env`
- Ensure database exists: `psql -l`

### Frontend Issues

**Problem**: API connection errors
- Verify backend is running on port 8000
- Check VITE_API_BASE_URL in `.env`
- Inspect browser console for CORS errors

**Problem**: Build failures
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

---

## 🗺 Roadmap

### Phase 1: Core Features (Current)
- ✅ Patient registration and management
- ✅ Clinical event tracking
- ✅ Referral system
- ✅ User authentication and authorization
- ✅ Basic AI risk assessment

### Phase 2: Enhanced Features (Q2 2026)
- 🔄 Offline-first support for PHCs
- 🔄 Nepali language UI (i18n)
- 🔄 SMS/email alerts for high-risk cases
- 🔄 Advanced analytics dashboard
- 🔄 Mobile app (iOS/Android)

### Phase 3: Integration & Scale (Q3 2026)
- 📅 Integration with national health information systems
- 📅 District and provincial dashboards
- 📅 Telemedicine consultation features
- 📅 Multi-facility synchronization
- 📅 Advanced ML models for risk prediction

---

## 🤝 Contributing

We welcome contributions from the community! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guide for Python code
- Use TypeScript for all frontend code
- Write tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**SmartAama is a clinical decision support system and does not replace professional medical judgment.**

- This software is intended to assist healthcare providers in clinical decision-making
- All AI-generated recommendations are advisory only
- Healthcare providers maintain full responsibility for clinical decisions
- Use in compliance with national maternal health guidelines and applicable regulations
- Not FDA approved or cleared for clinical use

---

## 📞 Contact & Support

- **Documentation**: [docs.smartaama.com](https://docs.smartaama.com)
- **Issue Tracker**: [GitHub Issues](https://github.com/yourusername/smartaama/issues)
- **Email**: support@smartaama.com
- **Website**: [smartaama.com](https://smartaama.com)

---

<p align="center">
  <strong>Built with ❤️ for improving maternal health outcomes in Nepal</strong>
</p>

<p align="center">
  <sub>SmartAama © 2026. All rights reserved.</sub>
</p>