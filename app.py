from flask import Flask, render_template, request, session, redirect
import sqlite3
import random
import os

from questions import get_questions

app = Flask(__name__)
app.secret_key = "smart-trash-secret-key"

QUESTIONS = get_questions()
QUESTIONS_PER_ROUND = 100


def get_db():
    conn = sqlite3.connect("smarttrash.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            score INTEGER DEFAULT 0,
            items INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS answered_questions (
            player_name TEXT,
            question_id INTEGER,
            UNIQUE(player_name, question_id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# HOME
# =========================

@app.route("/")
def index():
    conn = get_db()

    players = conn.execute("""
        SELECT name, score, items
        FROM players
        ORDER BY score DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        players=players
    )


# =========================
# SET NAME
# =========================

@app.route("/set_name", methods=["POST"])
def set_name():
    name = request.form.get("name", "").strip()

    if not name:
        return redirect("/")

    session["player"] = name

    conn = get_db()

    player = conn.execute(
        "SELECT * FROM players WHERE name = ?",
        (name,)
    ).fetchone()

    if not player:
        conn.execute(
            "INSERT INTO players (name, score, items) VALUES (?, 0, 0)",
            (name,)
        )
        conn.commit()

    conn.close()

    return redirect("/")


# =========================
# CHANGE NAME
# =========================

@app.route("/change_name", methods=["POST"])
def change_name():
    old_name = session.get("player")
    new_name = request.form.get("name", "").strip()

    if not old_name or not new_name:
        return redirect("/")

    conn = get_db()

    existing = conn.execute(
        "SELECT * FROM players WHERE name = ?",
        (new_name,)
    ).fetchone()

    if not existing:
        conn.execute(
            "UPDATE players SET name = ? WHERE name = ?",
            (new_name, old_name)
        )

        conn.execute(
            "UPDATE answered_questions SET player_name = ? WHERE player_name = ?",
            (new_name, old_name)
        )

        conn.commit()

        session["player"] = new_name

    conn.close()

    return redirect("/")


# =========================
# START NEW QUIZ
# =========================

@app.route("/start_quiz")
def start_quiz():
    player = session.get("player")

    if not player:
        return redirect("/")

    conn = get_db()

    # Reset score
    conn.execute("""
        UPDATE players
        SET score = 0,
            items = 0
        WHERE name = ?
    """, (player,))

    # Remove old answered questions
    conn.execute("""
        DELETE FROM answered_questions
        WHERE player_name = ?
    """, (player,))

    conn.commit()
    conn.close()

    # Clear old round
    session.pop("round_questions", None)
    session.pop("current_question", None)

    return redirect("/quiz")


# =========================
# QUIZ
# =========================

@app.route("/SmartTrash")
@app.route("/quiz")
def quiz():
    player = session.get("player")

    if not player:
        return redirect("/")

    conn = get_db()

    answered_rows = conn.execute("""
        SELECT question_id
        FROM answered_questions
        WHERE player_name = ?
    """, (player,)).fetchall()

    answered_ids = {
        row["question_id"]
        for row in answered_rows
    }

    player_data = conn.execute("""
        SELECT score, items
        FROM players
        WHERE name = ?
    """, (player,)).fetchone()

    conn.close()

    # ==================================
    # CREATE RANDOM ROUND
    # ==================================

    round_questions = session.get("round_questions")

    if not round_questions:

        all_ids = [q["id"] for q in QUESTIONS]

        # If there are more than 100 questions,
        # randomly choose 100.
        if len(all_ids) > QUESTIONS_PER_ROUND:
            round_questions = random.sample(
                all_ids,
                QUESTIONS_PER_ROUND
            )

        # If there are exactly 100 questions,
        # shuffle all 100.
        else:
            round_questions = all_ids[:]
            random.shuffle(round_questions)

        session["round_questions"] = round_questions

    # ==================================
    # FIND NEXT QUESTION
    # ==================================

    available_ids = [
        question_id
        for question_id in round_questions
        if question_id not in answered_ids
    ]

    # ==================================
    # QUIZ FINISHED
    # ==================================

    if not available_ids:

        session.pop("round_questions", None)
        session.pop("current_question", None)

        return render_template(
            "quiz.html",
            finished=True,
            score=player_data["score"],
            correct=player_data["items"],
            total=QUESTIONS_PER_ROUND
        )

    # ==================================
    # GET NEXT RANDOM QUESTION
    # ==================================

    next_id = available_ids[0]

    question = next(
        q for q in QUESTIONS
        if q["id"] == next_id
    )

    # Save current question
    session["current_question"] = question["id"]

    # ==================================
    # CALCULATE DISPLAY NUMBER
    # ==================================

    answered_in_round = len(answered_ids)

    question_number = answered_in_round + 1

    # Make sure it doesn't exceed round size
    if question_number > len(round_questions):
        question_number = len(round_questions)

    return render_template(
        "quiz.html",
        question=question,
        question_number=question_number,
        total_questions=len(round_questions),
        score=player_data["score"],
        correct=player_data["items"],
        finished=False
    )


# =========================
# ANSWER
# =========================

@app.route("/answer", methods=["POST"])
def answer():
    player = session.get("player")

    if not player:
        return redirect("/")

    question_id = session.get("current_question")

    if question_id is None:
        return redirect("/quiz")

    selected_answer = request.form.get("answer")

    question = next(
        (
            q for q in QUESTIONS
            if q["id"] == question_id
        ),
        None
    )

    if question is None:
        return redirect("/quiz")

    conn = get_db()

    # Prevent answering the same question twice
    already_answered = conn.execute("""
        SELECT 1
        FROM answered_questions
        WHERE player_name = ?
        AND question_id = ?
    """, (player, question_id)).fetchone()

    if already_answered:
        conn.close()
        return redirect("/quiz")

    correct_answer = question["answer"]

    is_correct = selected_answer == correct_answer

    if is_correct:

        conn.execute("""
            UPDATE players
            SET score = score + 10,
                items = items + 1
            WHERE name = ?
        """, (player,))

    conn.execute("""
        INSERT INTO answered_questions
        (player_name, question_id)
        VALUES (?, ?)
    """, (player, question_id))

    conn.commit()

    player_data = conn.execute("""
        SELECT score, items
        FROM players
        WHERE name = ?
    """, (player,)).fetchone()

    conn.close()

    # ==================================
    # FIND CURRENT ROUND POSITION
    # ==================================

    round_questions = session.get("round_questions", [])

    try:
        question_number = (
            round_questions.index(question_id) + 1
        )
    except ValueError:
        question_number = 1

    return render_template(
        "quiz.html",
        question=question,
        selected_answer=selected_answer,
        is_correct=is_correct,
        answered=True,
        question_number=question_number,
        total_questions=len(round_questions),
        score=player_data["score"],
        correct=player_data["items"],
        finished=False
    )


# =========================
# LEADERBOARD
# =========================

@app.route("/leaderboard")
def leaderboard():
    conn = get_db()

    players = conn.execute("""
        SELECT name, score, items
        FROM players
        ORDER BY score DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        players=players
    )


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
