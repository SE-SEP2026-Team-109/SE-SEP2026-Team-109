"""C2 Profile (US-02, US-03, US-04), C3 Tags, C4 Directory (US-05)."""

from tests.conftest import auth


def _ids(client, h):
    return {u["name"]: u["id"] for u in client.get("/api/mentors?page_size=100", headers=h).get_json()["items"]}


# ---------------- C2 Profile ----------------

def test_student_updates_own_profile(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    r = seeded.put("/api/profile/me", headers=h, json={"name": "Aarav S", "student": {
        "mneeds": "Portfolio help", "courselevel": "diploma", "skills": [{"name": "SQL", "level": 3, "want": True}]}})
    assert r.status_code == 200
    s = r.get_json()["student"]
    assert s["mneeds"] == "Portfolio help" and s["courselevel"] == "diploma" and s["skills"][0]["want"] is True
    assert seeded.get("/api/profile/me", headers=h).get_json()["name"] == "Aarav S"  # persisted


def test_foundation_clears_course_level(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    r = seeded.put("/api/profile/me", headers=h, json={"student": {"clear_courselevel": True}})
    assert r.get_json()["student"]["courselevel"] is None


def test_student_cannot_send_mentor_fields_and_unknown_fields_rejected(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    assert seeded.put("/api/profile/me", headers=h, json={"mentor": {"capacity": 3}}).status_code == 400
    assert seeded.put("/api/profile/me", headers=h, json={"role": "admin"}).status_code == 400


def test_mentor_capacity_and_pause(seeded):
    h = auth(seeded, "mentor@mentorconnect.demo")
    r = seeded.put("/api/profile/me", headers=h, json={"mentor": {"capacity": 5, "pause": True}})
    assert r.status_code == 200 and r.get_json()["mentor"]["capacity"] == 5 and r.get_json()["mentor"]["pause"] is True
    assert seeded.put("/api/profile/me", headers=h, json={"mentor": {"capacity": 11}}).status_code == 400
    assert seeded.put("/api/profile/me", headers=h, json={"mentor": {"capacity": 0}}).status_code == 400


def test_username_must_be_unique(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    assert seeded.put("/api/profile/me", headers=h, json={"username": "priya_nair"}).status_code == 409


def test_photo_validation(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    assert seeded.put("/api/profile/me", headers=h, json={"photo": "javascript:alert(1)"}).status_code == 400
    assert seeded.put("/api/profile/me", headers=h, json={"photo": "data:image/jpeg;base64,AAAA"}).status_code == 200


def test_tag_limits_and_approval(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    six = ["Data Science", "Machine Learning", "Career Switch", "Backend", "System Design", "Internships"]
    assert seeded.put("/api/profile/me/tags", headers=h, json={"names": six}).status_code == 400  # > 5
    assert seeded.put("/api/profile/me/tags", headers=h, json={"names": ["UX Design"]}).status_code == 400  # pending
    r = seeded.put("/api/profile/me/tags", headers=h, json={"names": six[:5]})
    assert r.status_code == 200 and len(r.get_json()["tags"]) == 5


def test_email_hidden_until_accepted(seeded):
    s1 = auth(seeded, "student@mentorconnect.demo")
    ids = _ids(seeded, s1)
    priya = seeded.get(f"/api/mentors/{ids['Priya Nair']}", headers=s1).get_json()
    assert priya["email"] is None and priya["phone"] is None  # s1 only has a pending request
    meera = auth(seeded, "meera.iyer@ds.study.iitm.ac.in")  # accepted by Priya in the seed
    assert seeded.get(f"/api/mentors/{ids['Priya Nair']}", headers=meera).get_json()["email"] == "mentor@mentorconnect.demo"


def test_student_card_access(seeded):
    priya = auth(seeded, "mentor@mentorconnect.demo")
    reqs = seeded.get("/api/requests", headers=priya).get_json()
    sid = next(r["sid"] for r in reqs if r["status"] == "pending")
    assert seeded.get(f"/api/students/{sid}/card", headers=priya).status_code == 200
    # a mentor without any request from this student gets 404, and students get 403
    ananya_h = auth(seeded, "ananya.rao@alumni.demo")
    meera_id = next(r["sid"] for r in reqs if r["status"] == "accepted")
    assert seeded.get(f"/api/students/{meera_id}/card", headers=ananya_h).status_code == 404
    s1 = auth(seeded, "student@mentorconnect.demo")
    assert seeded.get(f"/api/students/{sid}/card", headers=s1).status_code == 403


def test_unverified_mentor_profile_is_404_for_students(seeded):
    admin = auth(seeded, "admin@mentorconnect.demo")
    isha = next(u for u in seeded.get("/api/admin/users", headers=admin).get_json() if u["name"] == "Isha Verma")
    s1 = auth(seeded, "student@mentorconnect.demo")
    assert seeded.get(f"/api/mentors/{isha['id']}", headers=s1).status_code == 404


# ---------------- C3 Tags ----------------

def test_tags_public_list_only_approved(seeded):
    names = [t["name"] for t in seeded.get("/api/tags").get_json()]
    assert "Data Science" in names and "UX Design" not in names


def test_suggest_and_admin_approve_reject(seeded):
    s1 = auth(seeded, "student@mentorconnect.demo")
    r = seeded.post("/api/tags/suggest", headers=s1, json={"name": "Quant Finance"})
    assert r.status_code == 201 and r.get_json()["approved"] is False
    assert seeded.post("/api/tags/suggest", headers=s1, json={"name": "quant finance"}).status_code == 409
    tag_id = r.get_json()["id"]
    assert seeded.patch(f"/api/admin/tags/{tag_id}", headers=s1, json={"action": "approve"}).status_code == 403
    admin = auth(seeded, "admin@mentorconnect.demo")
    assert seeded.patch(f"/api/admin/tags/{tag_id}", headers=admin, json={"action": "approve"}).get_json()["approved"] is True
    assert "Quant Finance" in [t["name"] for t in seeded.get("/api/tags").get_json()]
    pending = next(t for t in seeded.get("/api/admin/tags", headers=admin).get_json() if t["name"] == "UX Design")
    assert seeded.patch(f"/api/admin/tags/{pending['id']}", headers=admin, json={"action": "reject"}).status_code == 200
    assert seeded.post("/api/admin/tags", headers=admin, json={"name": "Robotics"}).status_code == 201


# ---------------- C4 Directory ----------------

def test_directory_lists_only_verified_and_computes_slots(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    body = seeded.get("/api/mentors", headers=h).get_json()
    names = [m["name"] for m in body["items"]]
    assert "Isha Verma" not in names and body["total"] == 6
    rahul = next(m for m in body["items"] if m["name"] == "Rahul Menon")
    assert rahul["mentor"]["free_slots"] == 0 and rahul["can_request"] is False  # capacity 1, one mentee
    vikram = next(m for m in body["items"] if m["name"] == "Dr. Vikram Seth")
    assert vikram["mentor"]["pause"] is True and vikram["mentor"]["free_slots"] == 0


def test_directory_filters_and_sorts(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    get = lambda qs: [m["name"] for m in seeded.get(f"/api/mentors?{qs}", headers=h).get_json()["items"]]
    assert get("q=finlytics") == ["Priya Nair"]
    assert get("q=nlp") == ["Dr. Vikram Seth"]  # matches a tag
    assert get("industry=Finance") == ["Neha Kulkarni"]
    assert get("area=Research") == ["Dr. Vikram Seth"]
    assert set(get("expertise=Career Switch")) == {"Priya Nair", "Ananya Rao"}
    assert "Rahul Menon" not in get("has_slots=true")
    assert get("sort=experience")[0] == "Neha Kulkarni"
    assert get("sort=free_slots")[0] == "Neha Kulkarni"
    assert seeded.get("/api/mentors?sort=bogus", headers=h).status_code == 400


def test_directory_pagination_and_roles(seeded):
    h = auth(seeded, "student@mentorconnect.demo")
    body = seeded.get("/api/mentors?page_size=4&page=2", headers=h).get_json()
    assert len(body["items"]) == 2 and body["total_pages"] == 2
    mentor = auth(seeded, "mentor@mentorconnect.demo")
    assert seeded.get("/api/mentors", headers=mentor).status_code == 403


def test_admin_verifies_mentor_then_visible(seeded):
    admin = auth(seeded, "admin@mentorconnect.demo")
    isha = next(u for u in seeded.get("/api/admin/users", headers=admin).get_json() if u["name"] == "Isha Verma")
    r = seeded.patch(f"/api/admin/mentors/{isha['id']}/verification", headers=admin, json={"status": "verified"})
    assert r.status_code == 200 and r.get_json()["mentor"]["veri_status"] == "verified"
    s1 = auth(seeded, "student@mentorconnect.demo")
    assert "Isha Verma" in _ids(seeded, s1)
    assert seeded.get("/api/admin/users", headers=s1).status_code == 403
