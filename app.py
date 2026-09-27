from flask import Flask, render_template, request, session, redirect
import sqlite3
import random
import os

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

    username = session.get("player")

    conn = get_db()

    players = conn.execute("""
        SELECT name, score, items
        FROM players
        ORDER BY score DESC, name ASC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        players=players,
        username=username
    )


# =========================
# SET NAME
# =========================

@app.route("/set_name", methods=["POST"])
def set_name():

    name = request.form.get("name", "").strip()

    if not name:
        return redirect("/")

    # Limit name length
    name = name[:20]

    conn = get_db()

    player = conn.execute(
        "SELECT * FROM players WHERE name = ?",
        (name,)
    ).fetchone()

    # Create new player if needed
    if not player:

        conn.execute("""
            INSERT INTO players
            (name, score, items)
            VALUES (?, 0, 0)
        """, (name,))

        conn.commit()

    conn.close()

    # Set current player
    session["player"] = name

    # Remove previous quiz session
    session.pop("round_questions", None)
    session.pop("current_question", None)

    # Start a fresh quiz
    return redirect("/start_quiz")


# =========================
# CHANGE / SWITCH NAME
# =========================

@app.route("/change_name", methods=["POST"])
def change_name():

    new_name = request.form.get("name", "").strip()

    if not new_name:
        return redirect("/")

    new_name = new_name[:20]

    conn = get_db()

    # Check whether this name already exists
    existing = conn.execute("""
        SELECT *
        FROM players
        WHERE name = ?
    """, (new_name,)).fetchone()

    conn.close()

    # If the player already exists,
    # simply switch to that player.
    if existing:

        session["player"] = new_name

        session.pop("round_questions", None)
        session.pop("current_question", None)

        return redirect("/start_quiz")

    # Otherwise create a new player
    conn = get_db()

    conn.execute("""
        INSERT INTO players
        (name, score, items)
        VALUES (?, 0, 0)
    """, (new_name,))

    conn.commit()
    conn.close()

    session["player"] = new_name

    session.pop("round_questions", None)
    session.pop("current_question", None)

    return redirect("/start_quiz")


# =========================
# SWITCH PLAYER
# =========================

@app.route("/switch_player")
def switch_player():

    # Clear current player
    session.pop("player", None)

    # Clear quiz session
    session.pop("round_questions", None)
    session.pop("current_question", None)

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

    # Reset THIS player's score
    conn.execute("""
        UPDATE players
        SET score = 0,
            items = 0
        WHERE name = ?
    """, (player,))

    # Reset THIS player's answered questions
    conn.execute("""
        DELETE FROM answered_questions
        WHERE player_name = ?
    """, (player,))

    conn.commit()
    conn.close()

    # Remove old random round
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

    # Get answered questions
    answered_rows = conn.execute("""
        SELECT question_id
        FROM answered_questions
        WHERE player_name = ?
    """, (player,)).fetchall()

    answered_ids = {
        row["question_id"]
        for row in answered_rows
    }

    # Get player information
    player_data = conn.execute("""
        SELECT score, items
        FROM players
        WHERE name = ?
    """, (player,)).fetchone()

    conn.close()

    if not player_data:
        session.pop("player", None)
        return redirect("/")


    # =========================
    # CREATE RANDOM ROUND
    # =========================

    round_questions = session.get("round_questions")

    if not round_questions:

        all_ids = [q["id"] for q in QUESTIONS]

        # More than 100 questions
        if len(all_ids) > QUESTIONS_PER_ROUND:

            round_questions = random.sample(
                all_ids,
                QUESTIONS_PER_ROUND
            )

        # Exactly 100 or fewer
        else:

            round_questions = all_ids[:]

            random.shuffle(round_questions)

        session["round_questions"] = round_questions


    # =========================
    # FIND NEXT QUESTION
    # =========================

    available_ids = [
        question_id
        for question_id in round_questions
        if question_id not in answered_ids
    ]


    # =========================
    # QUIZ FINISHED
    # =========================

    if not available_ids:

        total_questions = len(round_questions)

        session.pop("round_questions", None)
        session.pop("current_question", None)

        return render_template(
            "quiz.html",
            finished=True,
            score=player_data["score"],
            correct=player_data["items"],
            total=total_questions
        )


    # =========================
    # GET NEXT QUESTION
    # =========================

    next_id = available_ids[0]

    question = next(
        q for q in QUESTIONS
        if q["id"] == next_id
    )

    session["current_question"] = question["id"]


    # =========================
    # DISPLAY NUMBER
    # =========================

    question_number = (
        len(round_questions) - len(available_ids) + 1
    )

    total_questions = len(round_questions)


    return render_template(
        "quiz.html",

        question=question,

        question_number=question_number,

        total_questions=total_questions,

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


    # =========================
    # PREVENT DOUBLE ANSWER
    # =========================

    already_answered = conn.execute("""
        SELECT 1
        FROM answered_questions
        WHERE player_name = ?
        AND question_id = ?
    """, (player, question_id)).fetchone()


    if already_answered:

        conn.close()

        return redirect("/quiz")


    # =========================
    # CHECK ANSWER
    # =========================

    correct_answer = question["answer"]

    is_correct = (
        selected_answer == correct_answer
    )


    # =========================
    # UPDATE SCORE
    # =========================

    if is_correct:

        conn.execute("""
            UPDATE players
            SET score = score + 10,
                items = items + 1
            WHERE name = ?
        """, (player,))


    # =========================
    # SAVE ANSWERED QUESTION
    # =========================

    conn.execute("""
        INSERT INTO answered_questions
        (player_name, question_id)
        VALUES (?, ?)
    """, (player, question_id))


    conn.commit()


    # =========================
    # GET UPDATED PLAYER DATA
    # =========================

    player_data = conn.execute("""
        SELECT score, items
        FROM players
        WHERE name = ?
    """, (player,)).fetchone()

    conn.close()


    # =========================
    # QUESTION NUMBER
    # =========================

    round_questions = session.get(
        "round_questions",
        []
    )

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
        ORDER BY score DESC, name ASC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        players=players,
        username=session.get("player")
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
