#!/usr/bin/env python
"""Test script to create a patient and verify changes"""
import sys
sys.path.insert(0, '.')

from app.db.session import engine, SessionLocal
from app.db.init_db import init_db
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.services.patient_service import PatientService
from app.schemas.patient import PatientCreate

# Create admin user if needed
db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            full_name="Admin User",
            role=UserRole.ADMIN,
            password_hash=hash_password("AdminPass123!"),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✓ Created admin user: {admin.username}")
    else:
        print(f"✓ Admin user already exists: {admin.username}")
    
    # Test patient ID generation and creation
    patient_data = PatientCreate(
        first_name="John",
        last_name="Doe",
        age_in_years=28,
        sex="Male",
        phone_number="+977-9841234567",
        district="Kathmandu",
        municipality="Kathmandu Metropolitan",
        occupation="Engineer",
        education_level="Bachelor",
        marital_status="Single"
    )
    
    patient = PatientService.create_patient(
        db,
        payload=patient_data,
        actor=admin,
        ip="127.0.0.1"
    )
    
    print(f"✓ Created patient with ID: {patient.patient_id}")
    print(f"  - Full name: {patient.full_name}")
    print(f"  - Age: {patient.age_in_years} years")
    print(f"  - District: {patient.district}")
    print(f"  - Database ID: {patient.id}")
    
finally:
    db.close()
