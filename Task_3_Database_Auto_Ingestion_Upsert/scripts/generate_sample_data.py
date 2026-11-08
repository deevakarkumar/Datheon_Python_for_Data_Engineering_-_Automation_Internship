"""
Sample Dataset Generator Script
-------------------------------
Generates realistic initial (students.csv) and updated (students_updated.csv) datasets
with controlled variations to test insert, update, unchanged, and quarantine flows.
"""

from pathlib import Path
import random
import pandas as pd

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Priya", "Ananya", "Rahul", "Neha", "Vikram",
    "Sanya", "Ishaan", "Kavya", "Amit", "Diya", "Arjun", "Pooja", "Varun",
    "Sneha", "Karan", "Tanvi", "Aditya", "Rhea", "Manish", "Divya", "Siddharth",
    "Meera", "Gaurav", "Simran", "Nikhil", "Akanksha", "Kunal", "Shreya", "Deepak"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Mehta", "Patel", "Singh", "Kumar",
    "Joshi", "Bose", "Nair", "Rao", "Chopra", "Reddy", "Das", "Chatterjee",
    "Kapoor", "Mishra", "Pandey", "Saxena", "Bhatia", "Iyer", "Banerjee"
]

COURSES = [
    "Computer Science",
    "Data Science",
    "Artificial Intelligence",
    "Cybersecurity",
    "Cloud Computing",
    "Software Engineering",
]

def generate_datasets(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    # -------------------------------------------------------------
    # 1. Initial Dataset: 105 Students (STU001 to STU105)
    # -------------------------------------------------------------
    initial_records = []
    used_emails = set()

    for i in range(1, 106):
        sid = f"STU{i:03d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        name = f"{fname} {lname}"
        
        email_base = f"{fname.lower()}.{lname.lower()}{i}@university.edu"
        email = email_base
        counter = 1
        while email in used_emails:
            email = f"{fname.lower()}.{lname.lower()}{i}_{counter}@university.edu"
            counter += 1
        used_emails.add(email)

        course = random.choice(COURSES)
        marks = round(random.uniform(55.0, 98.5), 1)
        month = random.randint(1, 4)
        day = random.randint(1, 28)
        enroll_date = f"2024-{month:02d}-{day:02d}"
        last_updated = f"{enroll_date} 09:00:00"

        initial_records.append({
            "student_id": sid,
            "student_name": name,
            "email": email,
            "course": course,
            "marks": marks,
            "enrollment_date": enroll_date,
            "last_updated": last_updated,
        })

    initial_df = pd.DataFrame(initial_records)
    initial_path = output_dir / "students.csv"
    initial_df.to_csv(initial_path, index=False, encoding="utf-8")
    print(f"Generated initial dataset: {initial_path} ({len(initial_df)} records)")

    # -------------------------------------------------------------
    # 2. Updated Dataset: Demonstrating Upsert
    #    - 40 Unchanged records (STU001 - STU040)
    #    - 25 Updated records (STU041 - STU065) -> modified marks/course
    #    - 35 New records (STU106 - STU140)
    #    - 5 Intentionally Invalid records (STU991 - STU995)
    # -------------------------------------------------------------
    updated_records = []

    # A. 40 Unchanged (STU001 to STU040)
    for rec in initial_records[:40]:
        updated_records.append(rec.copy())

    # B. 25 Modified (STU041 to STU065)
    for rec in initial_records[40:65]:
        mod = rec.copy()
        # Change marks and course to simulate grade update & semester progression
        mod["marks"] = round(min(100.0, mod["marks"] + random.uniform(3.0, 8.0)), 1)
        current_course_idx = COURSES.index(mod["course"])
        mod["course"] = COURSES[(current_course_idx + 1) % len(COURSES)]
        mod["last_updated"] = "2024-05-10 14:30:00"
        updated_records.append(mod)

    # C. 35 Completely New Students (STU106 to STU140)
    for i in range(106, 141):
        sid = f"STU{i:03d}"
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        name = f"{fname} {lname}"
        email = f"{fname.lower()}.{lname.lower()}{i}@university.edu"
        course = random.choice(COURSES)
        marks = round(random.uniform(60.0, 99.0), 1)
        enroll_date = "2024-05-01"
        last_updated = "2024-05-01 10:00:00"

        updated_records.append({
            "student_id": sid,
            "student_name": name,
            "email": email,
            "course": course,
            "marks": marks,
            "enrollment_date": enroll_date,
            "last_updated": last_updated,
        })

    # D. 5 Intentionally Invalid Records (for validation testing)
    invalid_samples = [
        # 1. Negative marks (< 0)
        {
            "student_id": "STU991",
            "student_name": "Test Student NegativeMarks",
            "email": "test.negative@university.edu",
            "course": "Data Science",
            "marks": -15.5,
            "enrollment_date": "2024-05-02",
            "last_updated": "2024-05-02 11:00:00",
        },
        # 2. Missing mandatory name
        {
            "student_id": "STU992",
            "student_name": "",
            "email": "missing.name@university.edu",
            "course": "Artificial Intelligence",
            "marks": 85.0,
            "enrollment_date": "2024-05-02",
            "last_updated": "2024-05-02 11:00:00",
        },
        # 3. Invalid email regex
        {
            "student_id": "STU993",
            "student_name": "Test Student BadEmail",
            "email": "invalid-email-address-no-at-domain",
            "course": "Cybersecurity",
            "marks": 78.0,
            "enrollment_date": "2024-05-02",
            "last_updated": "2024-05-02 11:00:00",
        },
        # 4. Out-of-bounds marks (> 100)
        {
            "student_id": "STU994",
            "student_name": "Test Student OverMarks",
            "email": "over.marks@university.edu",
            "course": "Cloud Computing",
            "marks": 145.0,
            "enrollment_date": "2024-05-02",
            "last_updated": "2024-05-02 11:00:00",
        },
        # 5. Invalid date format (not YYYY-MM-DD)
        {
            "student_id": "STU995",
            "student_name": "Test Student BadDate",
            "email": "bad.date@university.edu",
            "course": "Software Engineering",
            "marks": 82.0,
            "enrollment_date": "99/99/9999",
            "last_updated": "2024-05-02 11:00:00",
        },
    ]

    updated_records.extend(invalid_samples)

    updated_df = pd.DataFrame(updated_records)
    updated_path = output_dir / "students_updated.csv"
    updated_df.to_csv(updated_path, index=False, encoding="utf-8")
    print(f"Generated updated dataset: {updated_path} ({len(updated_df)} records)")


if __name__ == "__main__":
    target_dir = Path(__file__).resolve().parent.parent / "data"
    generate_datasets(target_dir)
