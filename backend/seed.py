"""Seed database with sample wards, contractors, and demo users."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, Base, engine
from app import models
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Wards
wards_data = [
    ("Jayanagar", "South", 85000, 3.2, 78.5),
    ("Malleswaram", "West", 72000, 2.8, 82.1),
    ("Whitefield", "East", 150000, 6.4, 61.3),
    ("Koramangala", "South-East", 110000, 4.1, 71.0),
    ("Hebbal", "North", 95000, 7.8, 55.2),
    ("BTM Layout", "South", 130000, 5.3, 63.7),
    ("Yelahanka", "North", 88000, 6.9, 59.4),
    ("Marathahalli", "East", 140000, 7.2, 57.8),
]

ward_objs = []
for name, zone, pop, flood, clean in wards_data:
    existing = db.query(models.Ward).filter(models.Ward.name == name).first()
    if not existing:
        w = models.Ward(name=name, zone=zone, population=pop, flood_risk_score=flood, cleanliness_score=clean)
        db.add(w)
        ward_objs.append(w)
db.commit()
all_wards = db.query(models.Ward).all()

# Contractors
contractors_data = [
    ("CleanBengaluru Pvt Ltd", "9876543210", 0, 92.0, 48, 44),
    ("SwachhCity Services", "9876543211", 1, 78.5, 35, 27),
    ("GreenWaste Solutions", "9876543212", 2, 85.3, 60, 51),
    ("BBMP Direct Team A", "9876543213", 3, 95.0, 42, 40),
    ("EcoManage Corp", "9876543214", 4, 65.2, 55, 36),
]
for name, contact, ward_idx, score, assigned, resolved in contractors_data:
    existing = db.query(models.Contractor).filter(models.Contractor.name == name).first()
    if not existing:
        c = models.Contractor(
            name=name, contact=contact,
            ward_id=all_wards[ward_idx].id if ward_idx < len(all_wards) else None,
            compliance_score=score, total_assigned=assigned, total_resolved=resolved
        )
        db.add(c)
db.commit()

# Demo users
users_data = [
    ("Rahul Sharma", "citizen@demo.com", "9900001111", "demo1234", models.UserRole.citizen, 0),
    ("Priya Nair", "field@demo.com", "9900002222", "demo1234", models.UserRole.field_officer, 0),
    ("Kumar Swamy", "ward@demo.com", "9900003333", "demo1234", models.UserRole.ward_officer, 0),
    ("Commissioner Reddy", "commissioner@demo.com", "9900004444", "demo1234", models.UserRole.commissioner, None),
]
for name, email, phone, pwd, role, ward_idx in users_data:
    existing = db.query(models.User).filter(models.User.email == email).first()
    if not existing:
        u = models.User(
            name=name, email=email, phone=phone,
            hashed_password=hash_password(pwd),
            role=role,
            ward_id=all_wards[ward_idx].id if ward_idx is not None else None
        )
        db.add(u)
db.commit()
db.close()
print("✅ Database seeded successfully.")
print("\nDemo logins:")
print("  Citizen:        citizen@demo.com / demo1234")
print("  Field Officer:  field@demo.com / demo1234")
print("  Ward Officer:   ward@demo.com / demo1234")
print("  Commissioner:   commissioner@demo.com / demo1234")
