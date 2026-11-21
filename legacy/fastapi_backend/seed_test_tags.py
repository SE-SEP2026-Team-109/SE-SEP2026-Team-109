from app.database import SessionLocal
from app.models.enums import TagType
from app.models.tags import Tag


TEST_TAGS = [
    # Domains
    ("Artificial Intelligence", TagType.domain),
    ("Data Science", TagType.domain),
    ("Web Development", TagType.domain),
    ("Cybersecurity", TagType.domain),
    ("Cloud Computing", TagType.domain),

    # Expertise
    ("Machine Learning", TagType.expertise),
    ("Deep Learning", TagType.expertise),
    ("Natural Language Processing", TagType.expertise),
    ("Backend Development", TagType.expertise),
    ("Data Analysis", TagType.expertise),

    # Tools
    ("Python", TagType.tool),
    ("FastAPI", TagType.tool),
    ("React", TagType.tool),
    ("Docker", TagType.tool),
    ("TensorFlow", TagType.tool),
    ("SQL", TagType.tool),

    # Skills
    ("Communication", TagType.skill),
    ("Problem Solving", TagType.skill),
    ("Critical Thinking", TagType.skill),
    ("Teamwork", TagType.skill),
    ("Leadership", TagType.skill),
]


def seed_test_tags():
    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        for name, tag_type in TEST_TAGS:
            existing = (
                db.query(Tag)
                .filter(
                    Tag.name.ilike(name),
                    Tag.type == tag_type,
                )
                .first()
            )

            if existing:
                skipped += 1
                continue

            tag = Tag(
                name=name,
                type=tag_type,
                t_status=True,
            )

            db.add(tag)
            inserted += 1

        db.commit()

        print(f"Inserted: {inserted} tags")
        print(f"Skipped: {skipped} existing tags")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_test_tags()