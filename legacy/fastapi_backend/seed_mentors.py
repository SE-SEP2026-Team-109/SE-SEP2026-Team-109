
"""
Seed sample mentor accounts for testing the MentorConnect directory.

Run from the backend directory:
    python seed_mentors.py

The script is idempotent: running it more than once will not create
duplicate mentor accounts, profiles, tags, or user-tag associations.
"""

from app.database import SessionLocal
from app.core.security import hash_password

from app.models.user import User, Mentor, UserRole
from app.models.enums import (
    UserStatus,
    VerificationStatus,
    Course,
    CourseLevel,
    TagType,
)
from app.models.tags import Tag, UserTag


DEMO_PASSWORD = "Demo1234"


# Each mentor has a distinct profile, capacity and tag combination
# to make directory filtering and sorting easier to test.
MENTORS = [
    {
        "email": "mentor.priya@mentorconnect.demo",
        "username": "priya_mentor",
        "name": "Priya Nair",
        "designation": "Senior Data Scientist",
        "company": "Tata Consultancy Services",
        "bio": "Experienced data scientist interested in mentoring students in analytics and machine learning.",
        "experience": 8.0,
        "capacity": 5,
        "iitm_program": Course.data_science_and_applications,
        "level_completed": CourseLevel.bs_degree,
        "year_completed": 2018,
        "tags": [
            ("Technology", TagType.domain),
            ("Data Science", TagType.expertise),
            ("Python", TagType.skill),
            ("Machine Learning", TagType.skill),
            ("TensorFlow", TagType.tool),
        ],
    },
    {
        "email": "mentor.rahul@mentorconnect.demo",
        "username": "rahul_mentor",
        "name": "Rahul Mehta",
        "designation": "Software Engineer",
        "company": "Google",
        "bio": "Software engineer passionate about backend development and system design.",
        "experience": 6.0,
        "capacity": 3,
        "iitm_program": Course.data_science_and_applications,
        "level_completed": CourseLevel.bs_degree,
        "year_completed": 2020,
        "tags": [
            ("Technology", TagType.domain),
            ("Software Development", TagType.expertise),
            ("Python", TagType.skill),
            ("Java", TagType.skill),
            ("Docker", TagType.tool),
        ],
    },
    {
        "email": "mentor.ananya@mentorconnect.demo",
        "username": "ananya_mentor",
        "name": "Ananya Iyer",
        "designation": "Business Analyst",
        "company": "Deloitte",
        "bio": "Business analyst with experience in consulting, analytics and business strategy.",
        "experience": 5.0,
        "capacity": 4,
        "iitm_program": Course.management_and_data_science,
        "level_completed": CourseLevel.bsc_degree,
        "year_completed": 2021,
        "tags": [
            ("Finance", TagType.domain),
            ("Business Analytics", TagType.expertise),
            ("SQL", TagType.skill),
            ("Excel", TagType.tool),
        ],
    },
    {
        "email": "mentor.arjun@mentorconnect.demo",
        "username": "arjun_mentor",
        "name": "Arjun Menon",
        "designation": "Machine Learning Engineer",
        "company": "Microsoft",
        "bio": "Machine learning engineer interested in AI, deep learning and practical projects.",
        "experience": 10.0,
        "capacity": 8,
        "iitm_program": Course.data_science_and_applications,
        "level_completed": CourseLevel.bs_degree,
        "year_completed": 2016,
        "tags": [
            ("Technology", TagType.domain),
            ("Artificial Intelligence", TagType.expertise),
            ("Python", TagType.skill),
            ("Deep Learning", TagType.skill),
            ("PyTorch", TagType.tool),
        ],
    },
    {
        "email": "mentor.sneha@mentorconnect.demo",
        "username": "sneha_mentor",
        "name": "Sneha Kapoor",
        "designation": "Product Manager",
        "company": "Flipkart",
        "bio": "Product manager with experience in product strategy, design and agile development.",
        "experience": 7.0,
        "capacity": 2,
        "iitm_program": Course.management_and_data_science,
        "level_completed": CourseLevel.bs_degree,
        "year_completed": 2019,
        "tags": [
            ("E-commerce", TagType.domain),
            ("Product Management", TagType.expertise),
            ("Agile", TagType.skill),
            ("Jira", TagType.tool),
        ],
    },
    {
        "email": "mentor.vikram@mentorconnect.demo",
        "username": "vikram_mentor",
        "name": "Vikram Singh",
        "designation": "Cloud Engineer",
        "company": "Amazon Web Services",
        "bio": "Cloud engineer experienced in infrastructure, deployment and cloud architecture.",
        "experience": 4.0,
        "capacity": 0,
        "iitm_program": Course.electronic_systems,
        "level_completed": CourseLevel.bsc_degree,
        "year_completed": 2022,
        "tags": [
            ("Technology", TagType.domain),
            ("Cloud Computing", TagType.expertise),
            ("Linux", TagType.skill),
            ("AWS", TagType.tool),
        ],
    },
]


def get_or_create_tag(db, name: str, tag_type: TagType) -> Tag:
    """Return an existing approved tag or create it."""

    tag = (
        db.query(Tag)
        .filter(
            Tag.name.ilike(name),
            Tag.type == tag_type,
            Tag.t_status.is_(True),
        )
        .first()
    )

    if tag:
        return tag

    tag = Tag(
        name=name,
        type=tag_type,
        t_status=True,
    )
    db.add(tag)
    db.flush()

    return tag


def get_or_create_mentor(db, data: dict) -> User:
    """Create a mentor account and profile if they do not already exist."""

    user = db.query(User).filter(User.email == data["email"]).first()

    if user is None:
        user = User(
            email=data["email"],
            username=data["username"],
            name=data["name"],
            password=hash_password(DEMO_PASSWORD),
            role=UserRole.mentor,
            status=UserStatus.active,
        )
        db.add(user)
        db.flush()

    elif user.role != UserRole.mentor:
        raise ValueError(
            f"{data['email']} already belongs to a non-mentor account."
        )

    # Do not overwrite a profile that already exists.
    if user.mentor is None:
        mentor = Mentor(
            id=user.id,
            iitm_program=data["iitm_program"],
            level_completed=data["level_completed"],
            year_completed=data["year_completed"],
            designation=data["designation"],
            bio=data["bio"],
            company=data["company"],
            experience=data["experience"],
            capacity=data["capacity"],
            veri_status=VerificationStatus.verified,
            pause=False,
        )
        db.add(mentor)
        db.flush()

    return user


def attach_tags(db, user: User, tag_data: list) -> int:
    """Attach the mentor's approved tags without creating duplicate links."""

    added = 0

    for name, tag_type in tag_data:
        tag = get_or_create_tag(db, name, tag_type)

        association = (
            db.query(UserTag)
            .filter(
                UserTag.uid == user.id,
                UserTag.tag_id == tag.id,
            )
            .first()
        )

        if association is None:
            db.add(
                UserTag(
                    uid=user.id,
                    tag_id=tag.id,
                    want_to_learn=False,
                    skill_level=4 if tag_type in (
                        TagType.skill,
                        TagType.tool,
                    ) else None,
                )
            )
            added += 1

    return added


def seed_mentors() -> None:
    """Seed all sample mentors and commit them as one transaction."""

    db = SessionLocal()

    try:
        created_or_found = 0
        added_tags = 0

        for data in MENTORS:
            user = get_or_create_mentor(db, data)
            added_tags += attach_tags(db, user, data["tags"])
            created_or_found += 1

        db.commit()

        print("Mentor seeding completed successfully.")
        print(f"Mentors processed: {created_or_found}")
        print(f"New mentor-tag associations: {added_tags}")
        print(f"Demo password for newly created accounts: {DEMO_PASSWORD}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_mentors()
