"""Demo data, mirroring the frontend's former ``src/data/mock.js``.

Same people, emails and password (``Demo1234``) as the mock, so the login page's
one-click demo buttons and the team's demo script keep working. Runs only when
the database has no users, so it never overwrites real data.

Note: the demo student emails like ``student@mentorconnect.demo`` do not end in
study.iitm.ac.in. They are seeded directly (not through registration), exactly as
in the mock; the domain rule is enforced for everyone who registers.
"""

from datetime import timedelta

from sqlalchemy import func, select

from app.extensions import db
from app.models import (
    Course, CourseLevel, Mentor, Mentorship, MentorshipStatus, Notification, Request, RequestStatus,
    RequestStatusHistory, Student, Tag, TagType, User, UserRole, UserTag, VerificationStatus, utcnow,
)
from app.security import hash_password

PASSWORD = "Demo1234"
DEGREE = {"DS": Course.data_science_and_applications, "ES": Course.electronic_systems,
          "Management": Course.management_and_data_science, "Aero": Course.aeronautics_and_space_technology}
LEVEL = {"BS Degree": CourseLevel.bs_degree, "BSc": CourseLevel.bsc_degree, "Diploma": CourseLevel.diploma, "Foundation": None}

TAGS = ["Data Science", "Machine Learning", "Career Switch", "Backend", "System Design", "Internships",
        "Product Management", "Higher Studies", "Research", "NLP", "Data Analytics", "Finance", "Leadership",
        "Entrepreneurship", "Fundraising", "Software Engineering"]
SUGGESTED = ["UX Design", "Cloud Computing"]

STAFF = [
    ("a1", "admin", "Programme Admin", "admin@mentorconnect.demo", "programme_admin"),
    ("c1", "coordinator", "Kavya Reddy", "coordinator@mentorconnect.demo", "kavya_reddy"),
]
STUDENTS = [
    ("s1", "Aarav Sharma", "student@mentorconnect.demo", "aarav_s", "DS", "BS Degree", ["Data Science", "Product Management"],
     "Unsure whether to pursue a data role or higher studies; need help building a portfolio while working full time.",
     [("Python", 3, False), ("SQL", 2, True), ("Statistics", 2, True)], "24f1002112"),
    ("s2", "Meera Iyer", "meera.iyer@ds.study.iitm.ac.in", "meera_i", "DS", "BSc", ["Data Science"],
     "Wants to move from support work into analytics.", [("Excel", 4, False), ("Statistics", 2, True)], None),
    ("s3", "Rohan Das", "rohan.das@es.study.iitm.ac.in", "rohan_d", "ES", "Diploma", ["Software Engineering"],
     "Looking for backend internship guidance.", [("Java", 3, False), ("Git", 3, False)], None),
    ("s4", "Sneha Patil", "sneha.patil@ds.study.iitm.ac.in", "sneha_p", "DS", "BS Degree", ["Research", "Higher Studies"],
     "Considering a masters abroad and needs an honest view of the process.", [("Python", 4, False), ("ML", 3, True)], None),
    ("s5", "Karthik R", "karthik.r@ds.study.iitm.ac.in", "karthik_r", "Management", "Foundation", ["Entrepreneurship"],
     "Has a startup idea and no network.", [("Design", 2, False)], None),
]
MENTORS = [
    ("m1", "Priya Nair", "mentor@mentorconnect.demo", "priya_nair", "Senior Data Scientist", "Finlytics", 7, "Fintech", "Data Science",
     "Moved from a non-CS role into data science through the IITM BS programme. Happy to review resumes and portfolios.",
     ["Data Science", "Machine Learning", "Career Switch"], ["Resume review", "Mock interviews", "Career advice"], 3, False, True),
    ("m2", "Rahul Menon", "rahul.menon@alumni.demo", "rahul_menon", "Backend Engineer", "CloudNine Labs", 5, "Cloud", "Software Engineering",
     "Backend developer, working on distributed systems. Can guide on internships and system design basics.",
     ["Backend", "System Design", "Internships"], ["Mock interviews", "Project guidance"], 1, False, True),
    ("m3", "Ananya Rao", "ananya.rao@alumni.demo", "ananya_rao", "Product Manager", "Greenleaf", 6, "Consumer", "Product Management",
     "Product manager who started in QA. Can talk about the path into product roles.",
     ["Product Management", "Career Switch"], ["Career advice", "Resume review"], 2, False, True),
    ("m4", "Dr. Vikram Seth", "vikram.seth@alumni.demo", "vikram_seth", "PhD Researcher", "Univ. of Edinburgh", 4, "Academia", "Research",
     "Doing a PhD in NLP. Guidance on applications and research proposals.",
     ["Higher Studies", "Research", "NLP"], ["Application review", "Career advice"], 4, True, True),
    ("m5", "Neha Kulkarni", "neha.kulkarni@alumni.demo", "neha_k", "Analytics Lead", "Ledgerly", 8, "Finance", "Analytics",
     "Leads an analytics team in fintech. Can help with analyst-to-lead transitions.",
     ["Data Analytics", "Finance", "Leadership"], ["Career advice", "Mock interviews"], 3, False, True),
    ("m6", "Arjun Bhat", "arjun.bhat@alumni.demo", "arjun_bhat", "Founder", "Tinkerbench", 5, "EdTech", "Entrepreneurship",
     "Founded a hardware-education startup after graduating.",
     ["Entrepreneurship", "Fundraising"], ["Career advice", "Project guidance"], 2, False, True),
    ("m7", "Isha Verma", "isha.verma@alumni.demo", "isha_verma", "ML Engineer", "Vectorly", 3, "AI", "Data Science",
     "Applied ML engineer. Awaiting admin verification, so not yet visible to students.",
     ["Machine Learning", "Data Science"], ["Project guidance"], 2, False, False),
]
# key, student, mentor, status, age in days, message, mentor reason
REQUESTS = [
    ("r1", "s1", "m1", "pending", 2, "Hello Priya, I work full time in operations and want to move into data science. Could you guide me on building a portfolio?", None),
    ("r2", "s4", "m1", "pending", 1, "I am considering a masters in ML abroad and would value your perspective on how to decide between work and study.", None),
    ("r3", "s2", "m1", "accepted", 20, "I am in customer support and want to move into analytics. Could you review my learning plan and resume?", None),
    ("r4", "s3", "m2", "accepted", 15, "I am a diploma student targeting backend internships and need help with a project roadmap and interview prep.", None),
    ("r5", "s1", "m3", "rejected", 8, "Hi Ananya, I would like to understand how to move from operations into product management and what skills matter.",
     "My calendar is full this quarter. Please try a mentor with Data Science expertise."),
    ("r6", "s1", "m4", "pending", 15, "Dr. Seth, I am exploring research and would like feedback on how to prepare for PhD applications in the next two years.", None),
    ("r7", "s5", "m2", "pending", 9, "I have a startup idea and no network. I would like to learn how backend engineers evaluate early-stage products.", None),
]


def seed_if_empty() -> bool:
    if db.session.scalar(select(func.count(User.id))):
        return False
    now = utcnow()
    pw = hash_password(PASSWORD)  # hash once; all demo users share it
    tags = {}
    for name in TAGS:
        tags[name] = Tag(name=name, type=TagType.expertise, t_status=True)
    for name in SUGGESTED:
        db.session.add(Tag(name=name, type=TagType.expertise, t_status=False))
    db.session.add_all(tags.values())

    users = {}
    for key, role, name, email, username in STAFF:
        users[key] = User(name=name, email=email, username=username, role=UserRole(role), password=pw)
    db.session.add_all(users.values())

    for key, name, email, username, degree, level, interests, needs, skills, rollno in STUDENTS:
        u = User(name=name, email=email, username=username, role=UserRole.student, password=pw)
        u.student = Student(course=DEGREE[degree], courselevel=LEVEL[level], mneeds=needs, rollno=rollno,
                            skills=[{"name": n, "level": lv, "want": w} for n, lv, w in skills])
        u.user_tags = [UserTag(tag=tags[t]) for t in interests]
        users[key] = u
    for (key, name, email, username, title, company, years, industry, area, bio, expertise, support, capacity,
         paused, verified) in MENTORS:
        u = User(name=name, email=email, username=username, role=UserRole.mentor, password=pw)
        u.mentor = Mentor(designation=title, company=company, experience=years, industry=industry, career_area=area,
                          bio=bio, support_types=support, capacity=capacity, pause=paused,
                          veri_status=VerificationStatus.verified if verified else VerificationStatus.pending)
        u.user_tags = [UserTag(tag=tags[t]) for t in expertise]
        users[key] = u
    db.session.add_all(users.values())
    db.session.flush()

    for key, sk, mk, status, age, message, reason in REQUESTS:
        created = now - timedelta(days=age)
        req = Request(sid=users[sk].id, mid=users[mk].id, student_message=message, created_on=created,
                      expires_on=created + timedelta(days=14), status=RequestStatus(status), mentor_response=reason)
        db.session.add(req)
        db.session.flush()
        db.session.add(RequestStatusHistory(rid=req.id, from_status=None, to_status=RequestStatus.pending,
                                            actor_id=users[sk].id, actor_role="Student", changed_on=created))
        if status != "pending":
            decided = created + timedelta(days=2)
            req.changed_on = decided
            db.session.add(RequestStatusHistory(rid=req.id, from_status=RequestStatus.pending, to_status=RequestStatus(status),
                                                actor_id=users[mk].id, actor_role="Mentor", changed_on=decided))
        if status == "accepted":
            db.session.add(Mentorship(rid=req.id, start=created + timedelta(days=2), status=MentorshipStatus.active))

    for uk, text, link, age in [
        ("s1", "Ananya Rao declined your mentoring request", "/student/requests", 6),
        ("m1", "New mentoring request from Aarav Sharma", "/mentor/requests", 2),
        ("m1", "New mentoring request from Sneha Patil", "/mentor/requests", 1),
        ("a1", "New mentor Isha Verma is waiting for verification", "/admin/dashboard?tab=users", 1),
    ]:
        db.session.add(Notification(uid=users[uk].id, message=text, link=link, created_at=now - timedelta(days=age)))
    db.session.commit()
    return True
