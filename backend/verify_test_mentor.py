from app.database import SessionLocal
from app.models.user import Mentor
from app.models.enums import VerificationStatus

db = SessionLocal()

try:
    mentors = db.query(Mentor).all()

    for mentor in mentors:
        print(
            f"Mentor ID: {mentor.id}, "
            f"Verification: {mentor.veri_status}"
        )

    mentor_id = int(input("\nEnter mentor ID to verify: "))

    mentor = db.query(Mentor).filter(
        Mentor.id == mentor_id
    ).first()

    if mentor is None:
        print("Mentor not found.")
    else:
        mentor.veri_status = VerificationStatus.verified
        db.commit()
        print(f"Mentor {mentor_id} verified successfully.")

except Exception:
    db.rollback()
    raise

finally:
    db.close()