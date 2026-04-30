"""
IQ Quiz App - Flask Backend
Handles all routes, database operations, and scoring logic.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import json
import os

app = Flask(__name__)
app.secret_key = "iq_quiz_secret_key_2024"  # Required for session management

# ─── Database Setup ───────────────────────────────────────────────────────────

DB_PATH = "database.db"

def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    return conn

def init_db():
    """Create tables if they don't exist."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            score     INTEGER NOT NULL,
            iq        INTEGER NOT NULL,
            total     INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ─── Questions Bank ───────────────────────────────────────────────────────────

QUESTIONS = [
    {
        "id": 1,
        "question": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?",
        "options": ["Yes", "No", "Cannot determine", "Only some"],
        "answer": "Yes",
        "category": "Logic"
    },
    {
        "id": 2,
        "question": "What number comes next in the sequence: 2, 6, 12, 20, 30, ?",
        "options": ["40", "42", "44", "48"],
        "answer": "42",
        "category": "Pattern"
    },
    {
        "id": 3,
        "question": "Which word is the odd one out?",
        "options": ["Apple", "Mango", "Carrot", "Banana"],
        "answer": "Carrot",
        "category": "Verbal"
    },
    {
        "id": 4,
        "question": "A train travels 60 km in 45 minutes. What is its speed in km/h?",
        "options": ["75", "80", "90", "85"],
        "answer": "80",
        "category": "Math"
    },
    {
        "id": 5,
        "question": "Mirror is to Reflection as Camera is to:",
        "options": ["Lens", "Flash", "Photograph", "Film"],
        "answer": "Photograph",
        "category": "Analogy"
    },
    {
        "id": 6,
        "question": "If you rearrange the letters 'CIFAIPC', you get the name of a/an:",
        "options": ["Country", "City", "Ocean", "Animal"],
        "answer": "Ocean",
        "category": "Verbal"
    },
    {
        "id": 7,
        "question": "What is 15% of 200?",
        "options": ["25", "30", "35", "20"],
        "answer": "30",
        "category": "Math"
    },
    {
        "id": 8,
        "question": "Which shape has the most sides among these?",
        "options": ["Pentagon", "Hexagon", "Octagon", "Heptagon"],
        "answer": "Octagon",
        "category": "Spatial"
    },
    {
        "id": 9,
        "question": "Complete the analogy: Book : Library :: Painting : ?",
        "options": ["Artist", "Museum", "Canvas", "Frame"],
        "answer": "Museum",
        "category": "Analogy"
    },
    {
        "id": 10,
        "question": "A farmer has 17 sheep. All but 9 die. How many are left?",
        "options": ["8", "9", "17", "None"],
        "answer": "9",
        "category": "Logic"
    },
    {
        "id": 11,
        "question": "Find the missing number: 3, 9, 27, 81, ?",
        "options": ["162", "243", "189", "270"],
        "answer": "243",
        "category": "Pattern"
    },
    {
        "id": 12,
        "question": "If John is taller than Mary and Mary is taller than Tom, who is the shortest?",
        "options": ["John", "Mary", "Tom", "Cannot determine"],
        "answer": "Tom",
        "category": "Logic"
    },
    {
        "id": 13,
        "question": "What is the square root of 144?",
        "options": ["11", "12", "13", "14"],
        "answer": "12",
        "category": "Math"
    },
    {
        "id": 14,
        "question": "How many months have 28 days?",
        "options": ["1", "2", "3", "12"],
        "answer": "12",
        "category": "Logic"
    },
    {
        "id": 15,
        "question": "Which number does not belong: 2, 3, 5, 7, 11, 13, 16?",
        "options": ["2", "11", "16", "13"],
        "answer": "16",
        "category": "Pattern"
    },
]

TIME_PER_QUESTION = 20  # seconds

# ─── IQ Calculation ───────────────────────────────────────────────────────────

def calculate_iq(score, total):
    """
    Simple IQ estimation formula:
    Base IQ of 80, each correct answer adds points proportionally.
    Max IQ capped at 160 for full score.
    """
    percentage = (score / total) * 100
    iq = 80 + int((score / total) * 80)
    return min(iq, 160)

def get_iq_label(iq):
    """Return a descriptive label based on estimated IQ."""
    if iq >= 145: return "Genius", "🧠"
    if iq >= 130: return "Highly Gifted", "⭐"
    if iq >= 115: return "Above Average", "🚀"
    if iq >= 100: return "Average", "👍"
    if iq >= 90:  return "Low Average", "📚"
    return "Below Average", "💪"

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    """Home page — user enters their name to start the quiz."""
    return render_template("index.html")


@app.route("/quiz", methods=["POST"])
def quiz():
    """
    Start the quiz:
    - Save the user's name in session
    - Pass all questions and timer config to the template
    """
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("home"))

    session["name"] = name
    session["started"] = True

    return render_template(
        "quiz.html",
        questions=QUESTIONS,
        total=len(QUESTIONS),
        time_per_question=TIME_PER_QUESTION
    )


@app.route("/submit", methods=["POST"])
def submit():
    """
    Handle quiz submission:
    - Compare user answers to correct answers
    - Calculate score and IQ
    - Save result to database
    - Redirect to result page
    """
    if not session.get("started"):
        return redirect(url_for("home"))

    name = session.get("name", "Anonymous")
    answers = request.form  # User's selected answers (key = question id)

    score = 0
    results_detail = []

    for q in QUESTIONS:
        qid = str(q["id"])
        user_answer = answers.get(f"answer_{qid}", "")
        correct = q["answer"]
        is_correct = user_answer == correct
        if is_correct:
            score += 1

        results_detail.append({
            "question": q["question"],
            "user_answer": user_answer if user_answer else "No Answer",
            "correct_answer": correct,
            "is_correct": is_correct,
            "category": q["category"]
        })

    total = len(QUESTIONS)
    iq = calculate_iq(score, total)
    label, emoji = get_iq_label(iq)

    # Save to database
    conn = get_db()
    conn.execute(
        "INSERT INTO results (name, score, iq, total) VALUES (?, ?, ?, ?)",
        (name, score, iq, total)
    )
    conn.commit()
    conn.close()

    # Clear session
    session.pop("started", None)

    # Store result for display
    session["last_result"] = {
        "name": name,
        "score": score,
        "total": total,
        "iq": iq,
        "label": label,
        "emoji": emoji,
        "details": results_detail
    }

    return redirect(url_for("result"))


@app.route("/result")
def result():
    """Show the quiz result page."""
    data = session.get("last_result")
    if not data:
        return redirect(url_for("home"))
    return render_template("result.html", data=data)


@app.route("/leaderboard")
def leaderboard():
    """Show leaderboard sorted by highest score, then IQ."""
    conn = get_db()
    rows = conn.execute("""
        SELECT name, score, iq, total, created_at
        FROM results
        ORDER BY score DESC, iq DESC
        LIMIT 50
    """).fetchall()
    conn.close()

    entries = []
    for i, row in enumerate(rows, start=1):
        label, emoji = get_iq_label(row["iq"])
        entries.append({
            "rank": i,
            "name": row["name"],
            "score": row["score"],
            "total": row["total"],
            "iq": row["iq"],
            "label": label,
            "emoji": emoji,
            "date": row["created_at"][:10]  # Just the date part
        })

    return render_template("leaderboard.html", entries=entries)


@app.route("/api/questions")
def api_questions():
    """API endpoint to get questions as JSON (used by JS)."""
    return jsonify(QUESTIONS)


# ─── Run App ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()  # Ensure database and tables exist
    app.run(debug=True, port=5000)