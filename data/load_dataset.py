"""
Load college_dataset.csv into the active SQLite database (data/college.db).
Splits the denormalized CSV into students, courses, and enrollments relational tables.
"""

import csv
import sqlite3
from pathlib import Path

CSV_PATH = Path(r"d:\RAI\Datasets\college_dataset.csv")
DB_PATH = Path(r"d:\RAI\sde-sql\data\college.db")

def load_dataset(csv_path: Path = CSV_PATH, db_path: Path = DB_PATH):
    if not csv_path.exists():
        raise FileNotFoundError(f"Source CSV not found: {csv_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Read CSV  
    students_dict = {}
    courses_dict = {}
    enrollments_list = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s_id = int(row["student_id"])
            name = row["name"].strip()
            s_dept = row["student_department"].strip()
            year = int(row["year"])
            cgpa = float(row["cgpa"])

            students_dict[s_id] = (s_id, name, s_dept, year, cgpa)

            c_id = row["course_id"].strip()
            if c_id:
                c_name = row["course_name"].strip()
                c_dept = row["course_department"].strip()
                credits = int(row["credits"])
                courses_dict[c_id] = (c_id, c_name, c_dept, credits)

                sem = row["semester"].strip()
                marks = int(row["marks"])
                enrollments_list.append((s_id, c_id, sem, marks))

    # Connect to SQLite and recreate schema
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS enrollments;
    DROP TABLE IF EXISTS courses;
    DROP TABLE IF EXISTS students;

    CREATE TABLE students (
        student_id INTEGER PRIMARY KEY,
        name TEXT,
        department TEXT,
        year INTEGER,
        cgpa REAL
    );

    CREATE TABLE courses (
        course_id TEXT PRIMARY KEY,
        course_name TEXT,
        department TEXT,
        credits INTEGER
    );

    CREATE TABLE enrollments (
        student_id INTEGER,
        course_id TEXT,
        semester TEXT,
        marks INTEGER,
        FOREIGN KEY(student_id) REFERENCES students(student_id),
        FOREIGN KEY(course_id) REFERENCES courses(course_id)
    );
    """)

    # Insert data
    cur.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?)", list(students_dict.values()))
    cur.executemany("INSERT INTO courses VALUES (?, ?, ?, ?)", list(courses_dict.values()))
    cur.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?)", enrollments_list)

    conn.commit()
    conn.close()

    print(f"Successfully loaded dataset into {db_path}:")
    print(f"  • students:    {len(students_dict):,} records")
    print(f"  • courses:     {len(courses_dict):,} records")
    print(f"  • enrollments: {len(enrollments_list):,} records")

if __name__ == "__main__":
    load_dataset()
