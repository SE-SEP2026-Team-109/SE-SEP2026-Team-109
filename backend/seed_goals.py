
"""Seed sample career goals for existing student accounts.
   Usage: 
        python seed_goals.py <-- seed all existing student profiles
        python seed_goals.py -- email x@study.iitm.ac.in <-- seed one particular student
"""



import argparse
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.enums import (
    GoalVisibility,
    MentorshipStatus,
    TrackGoalStatus,
)
from app.models.goals import TrackGoal
from app.models.mentoring import Mentorship, Request
from app.models.user import Student, User


# Sample goals shared by every student selected for seeding.
# Mentorship-only goals are added separately when an active mentorship exists.
GOALS = [
    {
        "title": "Complete a Python project",
        "description": "Build a practical Python project and document it.",
        "status": TrackGoalStatus.todo,
        "visibility": GoalVisibility.private,
        "deadline_days": 30,
    },
    {
        "title": "Learn backend development",
        "description": "Study REST APIs, databases and backend architecture.",
        "status": TrackGoalStatus.in_progress,
        "visibility": GoalVisibility.private,
        "deadline_days": 45,
    },
    {
        "title": "Revise data structures",
        "description": "Revise common data structures and solve practice problems.",
        "status": TrackGoalStatus.done,
        "visibility": GoalVisibility.private,
        "deadline_days": 10,
    },
    {
        "title": "Explore machine learning",
        "description": "Learn fundamental machine learning concepts.",
        "status": TrackGoalStatus.todo,
        "visibility": GoalVisibility.all_mentors,
        "deadline_days": 60,
    },
    {
        "title": "Build a portfolio",
        "description": "Prepare and publish a portfolio showcasing completed work.",
        "status": TrackGoalStatus.in_progress,
        "visibility": GoalVisibility.all_mentors,
        "deadline_days": 90,
    },
    {
        "title": "Complete SQL practice",
        "description": "Practise SQL queries, joins and database design.",
        "status": TrackGoalStatus.done,
        "visibility": GoalVisibility.all_mentors,
        "deadline_days": 15,
    },
]


MENTORSHIP_ONLY_GOAL = {
    "title": "Prepare for mentor review",
    "description": "Prepare project progress and questions for the next mentoring session.",
    "status": TrackGoalStatus.todo,
    "visibility": GoalVisibility.mentorship_only,
    "deadline_days": 20,
}


def get_students(db, email: str | None = None) -> list[Student]:
    """
    Retrieve student profiles to seed.

    Args:
        db: Database session.
        email: Optional email address to select one student.

    Returns:
        A list of matching student profiles.
    """
    query = db.query(Student).join(User, Student.id == User.id)

    if email:
        query = query.filter(User.email == email)

    return query.all()


def get_active_mentorship(db, student_id: int) -> Mentorship | None:
    """
    Find an active mentorship belonging to a student.

    Args:
        db: Database session.
        student_id: ID of the student.

    Returns:
        An active mentorship, or None if one does not exist.
    """
    return (
        db.query(Mentorship)
        .join(Request, Mentorship.rid == Request.id)
        .filter(
            Request.sid == student_id,
            Mentorship.status == MentorshipStatus.active,
        )
        .first()
    )


def seed_goal(
    db,
    student_id: int,
    goal_data: dict,
    mentoring_id: int | None = None,
) -> bool:
    """
    Insert a sample goal if it does not already exist.

    Args:
        db: Database session.
        student_id: ID of the student who owns the goal.
        goal_data: Goal attributes.
        mentoring_id: Optional associated mentorship ID.

    Returns:
        True if a goal was inserted, otherwise False.
    """
    existing = (
        db.query(TrackGoal)
        .filter(
            TrackGoal.sid == student_id,
            TrackGoal.title == goal_data["title"],
        )
        .first()
    )

    if existing:
        return False

    db.add(
        TrackGoal(
            sid=student_id,
            mgid=mentoring_id,
            title=goal_data["title"],
            description=goal_data["description"],
            status=goal_data["status"],
            visibility=goal_data["visibility"],
            deadline=datetime.utcnow()
            + timedelta(days=goal_data["deadline_days"]),
        )
    )

    return True


def seed_goals(email: str | None = None) -> None:
    """
    Seed sample goals for existing student profiles.

    Args:
        email: Optional email address to seed for one student.
            If omitted, all existing student profiles are selected.
    """
    db = SessionLocal()

    try:
        students = get_students(db, email)

        if not students:
            if email:
                print(
                    f"No student profile found for {email}. "
                    "Check the email and ensure the student has completed registration."
                )
            else:
                print(
                    "No student profiles found. Register a student before seeding goals."
                )
            return

        inserted = 0
        skipped = 0

        for student in students:
            print(f"\nSeeding goals for student ID: {student.id}")

            for goal_data in GOALS:
                if seed_goal(db, student.id, goal_data):
                    inserted += 1
                else:
                    skipped += 1

            # A mentorship-only goal requires an active mentorship.
            mentorship = get_active_mentorship(db, student.id)

            if mentorship:
                if seed_goal(
                    db,
                    student.id,
                    MENTORSHIP_ONLY_GOAL,
                    mentoring_id=mentorship.id,
                ):
                    inserted += 1
                else:
                    skipped += 1
            else:
                print(
                    "No active mentorship found; "
                    "skipping mentorship-only goal."
                )

        db.commit()

        print("\nGoal seeding completed.")
        print(f"Students processed: {len(students)}")
        print(f"Goals inserted: {inserted}")
        print(f"Existing goals skipped: {skipped}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed sample goals for MentorConnect students."
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Seed goals for a specific student email only.",
    )

    args = parser.parse_args()
    seed_goals(args.email)
