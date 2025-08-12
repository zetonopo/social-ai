"""
Script to seed initial data into the database.
"""
import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User, Plan, Base
from app.core.security import get_password_hash
from app.core.config import settings
import json


def create_initial_plans(db: Session):
    """Create initial subscription plans."""
    plans_data = [
        {
            "name": "Free",
            "description": "Perfect for getting started",
            "monthly_price": 0.0,
            "yearly_price": 0.0,
            "requests_per_month": 100,
            "concurrent_requests": 1,
            "features": json.dumps([
                "100 API requests per month",
                "Basic AI models",
                "Email support"
            ])
        },
        {
            "name": "Pro",
            "description": "For growing businesses",
            "monthly_price": 29.0,
            "yearly_price": 290.0,
            "requests_per_month": 10000,
            "concurrent_requests": 5,
            "features": json.dumps([
                "10,000 API requests per month",
                "Advanced AI models",
                "Priority support",
                "Analytics dashboard"
            ])
        },
        {
            "name": "Enterprise",
            "description": "For large organizations",
            "monthly_price": 99.0,
            "yearly_price": 990.0,
            "requests_per_month": 100000,
            "concurrent_requests": 20,
            "features": json.dumps([
                "100,000 API requests per month",
                "All AI models",
                "24/7 phone support",
                "Custom integrations",
                "SLA guarantee"
            ])
        }
    ]
    
    for plan_data in plans_data:
        existing_plan = db.query(Plan).filter(Plan.name == plan_data["name"]).first()
        if not existing_plan:
            plan = Plan(**plan_data)
            db.add(plan)
            print(f"Created plan: {plan_data['name']}")
    
    db.commit()


def create_admin_user(db: Session):
    """Create initial admin user."""
    admin_email = settings.admin_email
    admin_password = settings.admin_password
    
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if not existing_admin:
        admin_user = User(
            email=admin_email,
            password_hash=get_password_hash(admin_password),
            is_active=True,
            is_superuser=True
        )
        db.add(admin_user)
        db.commit()
        print(f"Created admin user: {admin_email}")
    else:
        print(f"Admin user already exists: {admin_email}")


def main():
    """Main function to seed the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Seeding initial data...")
    db = SessionLocal()
    
    try:
        create_initial_plans(db)
        create_admin_user(db)
        print("Database seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
