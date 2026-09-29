"""
Database seeding script for SDE-SQL.
Creates a college database with students, courses, and enrollments.
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path("data/college.db")

def seed_database():
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing DB if it exists for a fresh start
    if DB_PATH.exists():
        DB_PATH.unlink()
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
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

    # Insert Students
    students = [
        (1, 'Alice Smith', 'CSE', 3, 8.7),
        (2, 'Bob Johnson', 'CSE', 4, 9.2),
        (3, 'Charlie Brown', 'ECE', 2, 7.5),
        (4, 'Diana Prince', 'MECH', 4, 8.1),
        (5, 'Evan Davis', 'CSE', 3, 6.8),
        (6, 'Fiona Clark', 'EEE', 2, 8.9),
        (7, 'George Wright', 'ECE', 4, 7.2),
        (8, 'Hannah Martin', 'CSE', 1, 9.5),
        (9, 'Ian Thompson', 'MECH', 3, 7.9),
        (10, 'Julia White', 'EEE', 4, 8.4)
    ]
    cursor.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?)", students)

    # Insert Courses
    courses = [
        ('CS101', 'Intro to Programming', 'CSE', 4),
        ('CS201', 'Data Structures', 'CSE', 4),
        ('EC101', 'Digital Logic', 'ECE', 3),
        ('ME101', 'Thermodynamics', 'MECH', 3),
        ('EE101', 'Circuit Analysis', 'EEE', 4),
        ('CS301', 'Databases', 'CSE', 4),
        ('HU101', 'Communication Skills', 'HUM', 2)
    ]
    cursor.executemany("INSERT INTO courses VALUES (?, ?, ?, ?)", courses)

    # Insert Enrollments
    enrollments = [
        (1, 'CS101', 'Fall2023', 85),
        (1, 'CS201', 'Spring2024', 88),
        (2, 'CS201', 'Spring2024', 92),
        (2, 'CS301', 'Fall2024', 95),
        (3, 'EC101', 'Fall2023', 78),
        (4, 'ME101', 'Spring2024', 82),
        (5, 'CS101', 'Fall2023', 65),
        (6, 'EE101', 'Fall2023', 90),
        (7, 'EC101', 'Fall2023', 75),
        (8, 'CS101', 'Fall2024', 96),
        (10, 'EE101', 'Fall2023', 86),
        (1, 'HU101', 'Fall2023', 80),
        (3, 'HU101', 'Fall2023', 85)
    ]
    cursor.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?)", enrollments)

    conn.commit()
    conn.close()
    print(f"Successfully seeded database at {DB_PATH}")

if __name__ == "__main__":
    seed_database()
