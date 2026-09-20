from flask import Flask, render_template, request, session, redirect
import sqlite3
from questions import get_questions

app = Flask(__name__)
app.secret_key = "smart-trash-secret-key"

QUESTIONS = get_questions()
QUESTIONS_PER_ROUND = 100


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect("smarttrash.db")
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 0,
            items INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS answered_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            UNIQUE(player_name, question_id)
        )
    """)

    conn.commit()
    conn.close()


# IMPORTANT FOR RENDER
setup_database()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    username = session.get("username")

    conn = get_db()

    rows = conn.execute("""
        SELECT name, score, items
        FROM players
        ORDER BY score DESC, items DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    leaderboard = []

    for row in rows:
        leaderboard.append({
            "name": row["name"],
            "score": row["score"],
            "items": row["items"]
        })

    return render_template(
        "index.html",
        username=username,
        leaderboard=leaderboard
    )


# =========================
# SET NAME
# =========================

@app.route("/set_name", methods=["POST"])
def set_name():
    name = request.form.get("name", "").strip()

    if not name:
        return redirect("/")

    if len(name) > 30:
        name = name[:30]

    conn = get_db()

    player = conn.execute(
        """
        SELECT name
        FROM players
        WHERE name = ?
        """,
        (name,)
    ).fetchone()

    if player is None:
        conn.execute(
            """
            INSERT INTO players
            (name, score, items)
            VALUES (?, 0, 0)
            """,
            (name,)
        )

        conn.commit()

    conn.close()

    session["username"] = name

    return redirect("/")


# =========================
# CHANGE NAME
# =========================

@app.route("/change_name", methods=["POST"])
def change_name():
    old_name = session.get("username")

    if not old_name:
        return redirect("/")

    new_name = request.form.get("name", "").strip()

    if not new_name:
        return redirect("/")

    if len(new_name) > 30:
        new_name = new_name[:30]

    conn = get_db()

    existing = conn.execute(
        """
        SELECT name
        FROM players
        WHERE name = ?
        """,
        (new_name,)
    ).fetchone()

    if existing is not None and new_name != old_name:
        conn.close()
        return redirect("/")

    conn.execute(
        """
        UPDATE players
        SET name = ?
        WHERE name = ?
        """,
        (new_name, old_name)
    )

    conn.execute(
        """
        UPDATE answered_questions
        SET player_name = ?
        WHERE player_name = ?
        """,
        (new_name, old_name)
    )

    conn.commit()
    conn.close()

    session["username"] = new_name

    return redirect("/")


# =========================
# START NEW QUIZ
# =========================

@app.route("/start_quiz")
def start_quiz():
    if "username" not in session:
        return redirect("/")

    name = session["username"]

    conn = get_db()

    conn.execute(
        """
        DELETE FROM answered_questions
        WHERE player_name = ?
        """,
        (name,)
    )

    conn.execute(
        """
        UPDATE players
        SET score = 0,
            items = 0
        WHERE name = ?
        """,
        (name,)
    )

    conn.commit()
    conn.close()

    session.pop("current_question", None)

    return redirect("/SmartTrash")


# =========================
# QUIZ
# =========================

@app.route("/SmartTrash")
def quiz():
    if "username" not in session:
        return redirect("/")

    name = session["username"]

    conn = get_db()

    answered_rows = conn.execute(
        """
        SELECT question_id
        FROM answered_questions
        WHERE player_name = ?
        """,
        (name,)
    ).fetchall()

    answered_ids = {
        row["question_id"]
        for row in answered_rows
    }

    player = conn.execute(
        """
        SELECT score, items
        FROM players
        WHERE name = ?
        """,
        (name,)
    ).fetchone()

    if player is None:
        conn.execute(
            """
            INSERT OR IGNORE INTO players
            (name, score, items)
            VALUES (?, 0, 0)
            """,
            (name,)
        )

        conn.commit()

        player = conn.execute(
            """
            SELECT score, items
            FROM players
            WHERE name = ?
            """,
            (name,)
        ).fetchone()

    conn.close()

    available = [
        q for q in QUESTIONS
        if q["id"] not in answered_ids
    ]

    if not available:
        return render_template(
            "quiz.html",
            question=None,
            completed=True,
            feedback=False,
            score=player["score"],
            items=player["items"],
            username=name
        )

    question = min(
        available,
        key=lambda q: q["id"]
    )

    session["current_question"] = question["id"]

    return render_template(
        "quiz.html",
        question=question,
        completed=False,
        feedback=False,
        score=player["score"],
        items=player["items"],
        username=name
    )


# =========================
# ANSWER
# =========================

@app.route("/answer", methods=["POST"])
def answer():
    if "username" not in session:
        return redirect("/")

    name = session["username"]

    question_id = session.get("current_question")

    if question_id is None:
        return redirect("/SmartTrash")

    question = None

    for q in QUESTIONS:
        if q["id"] == question_id:
            question = q
            break

    if question is None:
        session.pop("current_question", None)
        return redirect("/SmartTrash")

    selected_answer = request.form.get("answer")
    correct_answer = question["answer"]

    is_correct = selected_answer == correct_answer

    conn = get_db()

    already_answered = conn.execute(
        """
        SELECT id
        FROM answered_questions
        WHERE player_name = ?
        AND question_id = ?
        """,
        (name, question_id)
    ).fetchone()

    if already_answered is not None:
        conn.close()
        session.pop("current_question", None)
        return redirect("/SmartTrash")

    if is_correct:
        conn.execute(
            """
            UPDATE players
            SET score = score + 10,
                items = items + 1
            WHERE name = ?
            """,
            (name,)
        )

    conn.execute(
        """
        INSERT INTO answered_questions
        (player_name, question_id)
        VALUES (?, ?)
        """,
        (name, question_id)
    )

    conn.commit()

    player = conn.execute(
        """
        SELECT score, items
        FROM players
        WHERE name = ?
        """,
        (name,)
    ).fetchone()

    answered_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM answered_questions
        WHERE player_name = ?
        """,
        (name,)
    ).fetchone()[0]

    conn.close()

    session.pop("current_question", None)

    if answered_count >= QUESTIONS_PER_ROUND:
        return render_template(
            "quiz.html",
            question=question,
            completed=True,
            feedback=True,
            is_correct=is_correct,
            selected_answer=selected_answer,
            correct_answer=correct_answer,
            score=player["score"],
            items=player["items"],
            username=name
        )

    return render_template(
        "quiz.html",
        question=question,
        completed=False,
        feedback=True,
        is_correct=is_correct,
        selected_answer=selected_answer,
        correct_answer=correct_answer,
        score=player["score"],
        items=player["items"],
        username=name
    )


# =========================
# LEADERBOARD
# =========================

@app.route("/leaderboard")
def leaderboard():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT name, score, items
        FROM players
        ORDER BY score DESC, items DESC
        LIMIT 100
        """
    ).fetchall()

    conn.close()

    leaderboard_data = []

    for row in rows:
        leaderboard_data.append({
            "name": row["name"],
            "score": row["score"],
            "items": row["items"]
        })

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard_data
    )


# =========================
# START SERVER
# =========================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
