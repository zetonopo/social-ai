# Social AI SaaS Platform

A comprehensive SaaS platform for AI-powered social media tools built with FastAPI, PostgreSQL, and Redis.

## Phase 1 - Foundation & Core Backend ✅

This phase includes:
- Complete project structure setup
- PostgreSQL database with SQLAlchemy models
- JWT-based authentication system
- User registration and login
- Password hashing with bcrypt
- Refresh token rotation
- Docker containerization
- Database migrations with Alembic

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)

### Setup

1. **Clone and navigate to the project:**
```bash
cd /path/to/social-ai
```

2. **Copy environment variables:**
```bash
cp .env.template backend/.env
# Edit backend/.env with your configuration
```

3. **Start with Docker Compose:**
```bash
docker-compose up -d postgres redis
```

4. **Install Python dependencies (for local development):**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

5. **Run database migrations:**
```bash
cd backend
alembic upgrade head
```

6. **Seed initial data:**
```bash
cd backend
python seed_data.py
```

7. **Start the application:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Authentication Endpoints

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get tokens
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (revoke refresh token)
- `GET /auth/me` - Get current user info
- `POST /auth/change-password` - Change password

### Database Models

- **User**: Basic user information and authentication
- **RefreshToken**: JWT refresh token management
- **Plan**: Subscription plans (Free, Pro, Enterprise)
- **Subscription**: User subscription to plans
- **UsageCounter**: Track API usage per user

### Default Admin User

- Email: admin@example.com
- Password: admin123

**⚠️ Change the admin password in production!**

## Environment Variables

Key configuration options in `.env`:

```env
DATABASE_URL=postgresql://social_ai_user:social_ai_password@localhost:5432/social_ai_db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Project Structure

```
backend/
├── app/
│   ├── core/           # Core functionality (config, database, auth)
│   ├── models/         # SQLAlchemy models
│   ├── routers/        # FastAPI route handlers
│   ├── schemas/        # Pydantic models
│   ├── services/       # Business logic
│   └── main.py         # FastAPI application
├── alembic/            # Database migrations
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
└── seed_data.py       # Initial data seeding
```

## Next Steps (Phase 2)

- User management endpoints
- Subscription management
- Admin panel functionality
- Role-based access control

## Testing the API

You can test the authentication flow using curl:

```bash
# Register a new user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Use the access token from login response
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```
