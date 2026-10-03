from flask import Flask, render_template, request, session, redirect
import sqlite3
import random
import os
import json

from questions import get_questions
from generator import generate_questions


app = Flask(__name__)

app.secret_key = "smart-trash-secret-key"


QUESTIONS = get_questions()
# Generated questions are loaded from SQLite below so their IDs and choices
# remain stable between server restarts.
GENERATED_QUESTIONS = []

QUESTIONS_PER_ROUND = 100



# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(
        "smarttrash.db"
    )

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


    conn.execute("""
        CREATE TABLE IF NOT EXISTS generated_questions (
            id INTEGER PRIMARY KEY,
            question TEXT UNIQUE NOT NULL,
            options_json TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    """)

    # Only insert new questions; never change the IDs of saved questions.
    original_ids = [q["id"] for q in QUESTIONS]
    first_id = max(original_ids, default=0) + 1
    existing = conn.execute(
        "SELECT id, question FROM generated_questions"
    ).fetchall()
    saved_texts = {row["question"] for row in existing}
    next_id = max([first_id - 1] + [row["id"] for row in existing]) + 1

    for q in generate_questions(start_id=first_id):
        if q["question"] not in saved_texts:
            conn.execute(
                "INSERT INTO generated_questions (id, question, options_json, answer) VALUES (?, ?, ?, ?)",
                (next_id, q["question"], json.dumps(q["options"], ensure_ascii=False), q["answer"])
            )
            saved_texts.add(q["question"])
            next_id += 1

    conn.commit()
    conn.close()



init_db()

def load_generated_questions():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, question, options_json, answer FROM generated_questions ORDER BY id"
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "question": r["question"],
             "options": json.loads(r["options_json"]), "answer": r["answer"]}
            for r in rows]

GENERATED_QUESTIONS = load_generated_questions()
QUESTIONS.extend(GENERATED_QUESTIONS)
QUESTION_BY_ID = {q["id"]: q for q in QUESTIONS}



# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

    username = session.get(
        "player"
    )


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



# =========================================================
# SET NAME
# =========================================================

@app.route(
    "/set_name",
    methods=["POST"]
)
def set_name():

    name = request.form.get(
        "name",
        ""
    ).strip()


    if not name:

        return redirect("/")


    name = name[:20]


    conn = get_db()


    player = conn.execute(

        "SELECT * FROM players WHERE name = ?",

        (name,)

    ).fetchone()


    if not player:

        conn.execute("""
            INSERT INTO players
            (name, score, items)
            VALUES (?, 0, 0)
        """, (name,))


        conn.commit()


    conn.close()


    session["player"] = name


    session.pop(
        "round_questions",
        None
    )

    session.pop(
        "current_question",
        None
    )


    session.pop(
        "quick_item",
        None
    )

    session.pop(
        "quick_score",
        None
    )

    session.pop(
        "quick_correct",
        None
    )

    session.pop(
        "quick_total",
        None
    )

    session.pop(
        "quick_answered",
        None
    )

    session.pop(
        "quick_streak",
        None
    )


    return redirect(
        "/start_quiz"
    )



# =========================================================
# CHANGE / SWITCH NAME
# =========================================================

@app.route(
    "/change_name",
    methods=["POST"]
)
def change_name():

    new_name = request.form.get(
        "name",
        ""
    ).strip()


    if not new_name:

        return redirect("/")


    new_name = new_name[:20]


    conn = get_db()


    existing = conn.execute("""
        SELECT *
        FROM players
        WHERE name = ?
    """, (new_name,)).fetchone()


    conn.close()


    if existing:

        session["player"] = new_name


        session.pop(
            "round_questions",
            None
        )

        session.pop(
            "current_question",
            None
        )


        session.pop(
            "quick_item",
            None
        )

        session.pop(
            "quick_score",
            None
        )

        session.pop(
            "quick_correct",
            None
        )

        session.pop(
            "quick_total",
            None
        )

        session.pop(
            "quick_answered",
            None
        )


        return redirect(
            "/start_quiz"
        )


    conn = get_db()


    conn.execute("""
        INSERT INTO players
        (name, score, items)
        VALUES (?, 0, 0)
    """, (new_name,))


    conn.commit()

    conn.close()


    session["player"] = new_name


    session.pop(
        "round_questions",
        None
    )

    session.pop(
        "current_question",
        None
    )


    session.pop(
        "quick_item",
        None
    )

    session.pop(
        "quick_score",
        None
    )

    session.pop(
        "quick_correct",
        None
    )

    session.pop(
        "quick_total",
        None
    )

    session.pop(
        "quick_answered",
        None
    )

    session.pop(
        "quick_streak",
        None
    )


    return redirect(
        "/start_quiz"
    )



# =========================================================
# SWITCH PLAYER
# =========================================================

@app.route(
    "/switch_player"
)
def switch_player():

    session.pop(
        "player",
        None
    )


    session.pop(
        "round_questions",
        None
    )

    session.pop(
        "current_question",
        None
    )


    session.pop(
        "quick_item",
        None
    )

    session.pop(
        "quick_score",
        None
    )

    session.pop(
        "quick_correct",
        None
    )

    session.pop(
        "quick_total",
        None
    )

    session.pop(
        "quick_answered",
        None
    )

    session.pop(
        "quick_streak",
        None
    )


    return redirect("/")



# =========================================================
# START NEW QUIZ
# =========================================================

@app.route(
    "/start_quiz"
)
def start_quiz():

    player = session.get(
        "player"
    )


    if not player:

        return redirect("/")


    conn = get_db()


    conn.execute("""
        UPDATE players
        SET score = 0,
            items = 0
        WHERE name = ?
    """, (player,))


    conn.execute("""
        DELETE FROM answered_questions
        WHERE player_name = ?
    """, (player,))


    conn.commit()

    conn.close()


    session.pop(
        "round_questions",
        None
    )

    session.pop(
        "current_question",
        None
    )


    return redirect(
        "/quiz"
    )



# =========================================================
# QUIZ
# =========================================================

@app.route("/SmartTrash")
@app.route("/quiz")
def quiz():

    player = session.get(
        "player"
    )


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


    if not player_data:

        session.pop(
            "player",
            None
        )

        return redirect("/")



    # =====================================================
    # CREATE RANDOM ROUND
    # =====================================================

    round_questions = session.get(
        "round_questions"
    )


    if not round_questions:
        unseen = [q["id"] for q in QUESTIONS if q["id"] not in answered_ids]
        if not unseen:
            # Every question was answered: start a fresh learning cycle.
            conn = get_db()
            conn.execute("DELETE FROM answered_questions WHERE player_name = ?", (player,))
            conn.commit()
            conn.close()
            answered_ids = set()
            unseen = [q["id"] for q in QUESTIONS]
        round_questions = random.sample(unseen, min(len(unseen), QUESTIONS_PER_ROUND))

        session["round_questions"] = (
            round_questions
        )



    # =====================================================
    # FIND NEXT QUESTION
    # =====================================================

    available_ids = [

        question_id

        for question_id in round_questions

        if question_id not in answered_ids

    ]



    # =====================================================
    # QUIZ FINISHED
    # =====================================================

    if not available_ids:

        total_questions = len(
            round_questions
        )


        session.pop(
            "round_questions",
            None
        )

        session.pop(
            "current_question",
            None
        )


        return render_template(

            "quiz.html",

            finished=True,

            score=player_data["score"],

            correct=player_data["items"],

            total=total_questions

        )



    # =====================================================
    # GET NEXT QUESTION
    # =====================================================

    next_id = available_ids[0]


    question = QUESTION_BY_ID[next_id]


    session["current_question"] = (
        question["id"]
    )



    # =====================================================
    # DISPLAY NUMBER
    # =====================================================

    question_number = (

        len(round_questions)

        - len(available_ids)

        + 1

    )


    total_questions = len(
        round_questions
    )


    return render_template(

        "quiz.html",

        question=question,

        question_number=question_number,

        total_questions=total_questions,

        score=player_data["score"],

        correct=player_data["items"],

        finished=False

    )



# =========================================================
# ANSWER NORMAL QUIZ
# =========================================================

@app.route(
    "/answer",
    methods=["POST"]
)
def answer():

    player = session.get(
        "player"
    )


    if not player:

        return redirect("/")


    question_id = session.get(
        "current_question"
    )


    if question_id is None:

        return redirect(
            "/quiz"
        )


    selected_answer = request.form.get(
        "answer"
    )


    question = next(

        (

            q

            for q in QUESTIONS

            if q["id"] == question_id

        ),

        None

    )


    if question is None:

        return redirect(
            "/quiz"
        )


    conn = get_db()



    # =====================================================
    # PREVENT DOUBLE ANSWER
    # =====================================================

    already_answered = conn.execute("""
        SELECT 1
        FROM answered_questions
        WHERE player_name = ?
        AND question_id = ?
    """, (
        player,
        question_id
    )).fetchone()


    if already_answered:

        conn.close()

        return redirect(
            "/quiz"
        )



    # =====================================================
    # CHECK ANSWER
    # =====================================================

    correct_answer = question[
        "answer"
    ]


    is_correct = (

        selected_answer

        == correct_answer

    )



    # =====================================================
    # UPDATE SCORE
    # =====================================================

    if is_correct:

        conn.execute("""
            UPDATE players
            SET score = score + 10,
                items = items + 1
            WHERE name = ?
        """, (player,))



    # =====================================================
    # SAVE ANSWERED QUESTION
    # =====================================================

    conn.execute("""
        INSERT INTO answered_questions
        (player_name, question_id)
        VALUES (?, ?)
    """, (
        player,
        question_id
    ))


    conn.commit()



    # =====================================================
    # UPDATED PLAYER DATA
    # =====================================================

    player_data = conn.execute("""
        SELECT score, items
        FROM players
        WHERE name = ?
    """, (player,)).fetchone()


    conn.close()



    # =====================================================
    # QUESTION NUMBER
    # =====================================================

    round_questions = session.get(

        "round_questions",

        []

    )


    try:

        question_number = (

            round_questions.index(
                question_id
            )

            + 1

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

        total_questions=len(
            round_questions
        ),

        score=player_data["score"],

        correct=player_data["items"],

        finished=False

    )



# =========================================================
# ⚡ QUICK SORT MODE
# =========================================================

QUICK_SORT_ITEMS = [
    {"name": "🥤 Chai nhựa", "answer": "recycle"},
    {"name": "🍎 Vỏ trái cây", "answer": "organic"},
    {"name": "🔋 Pin đã qua sử dụng", "answer": "dangerous"},
    {"name": "📄 Giấy vụn", "answer": "recycle"},
    {"name": "🥫 Lon nước ngọt", "answer": "recycle"},
    {"name": "🍌 Vỏ chuối", "answer": "organic"},
    {"name": "🧪 Chai hóa chất", "answer": "dangerous"},
    {"name": "🍚 Thức ăn thừa", "answer": "organic"},
    {"name": "🍾 Chai thủy tinh", "answer": "recycle"},
    {"name": "📰 Báo cũ", "answer": "recycle"},
    {"name": "☕ Bã cà phê", "answer": "organic"},
    {"name": "💊 Thuốc hết hạn", "answer": "dangerous"},
    {"name": "📦 Thùng carton", "answer": "recycle"},
    {"name": "🥬 Rau củ hỏng", "answer": "organic"},
    {"name": "💡 Bóng đèn hỏng", "answer": "dangerous"}
]


# =========================================================
# QUICK SORT DATABASE UPGRADE
# =========================================================

def upgrade_quick_sort_database():
    conn = get_db()
    columns = conn.execute("PRAGMA table_info(players)").fetchall()
    column_names = [column["name"] for column in columns]

    if "quick_best_streak" not in column_names:
        conn.execute("""
            ALTER TABLE players
            ADD COLUMN quick_best_streak INTEGER DEFAULT 0
        """)

    conn.commit()
    conn.close()


upgrade_quick_sort_database()


def get_quick_best_streak(username):
    conn = get_db()
    player = conn.execute("""
        SELECT quick_best_streak
        FROM players
        WHERE name = ?
    """, (username,)).fetchone()
    conn.close()

    if not player:
        return 0

    return player["quick_best_streak"] or 0


def get_quick_leaderboard():
    conn = get_db()
    players = conn.execute("""
        SELECT name, quick_best_streak
        FROM players
        WHERE quick_best_streak > 0
        ORDER BY quick_best_streak DESC, name ASC
        LIMIT 10
    """).fetchall()
    conn.close()
    return players


# =========================================================
# START QUICK SORT
# =========================================================

@app.route("/quick_sort")
def quick_sort():
    username = session.get("player")

    if not username:
        return redirect("/")

    session["quick_score"] = 0
    session["quick_correct"] = 0
    session["quick_total"] = 0
    session["quick_streak"] = 0
    session["quick_best_streak"] = get_quick_best_streak(username)
    session["quick_answered"] = False

    item = random.choice(QUICK_SORT_ITEMS)
    session["quick_item"] = item

    return render_template(
        "quick_sort.html",
        username=username,
        item=item,
        score=0,
        correct=0,
        total=0,
        streak=0,
        best_streak=get_quick_best_streak(username),
        new_best=False,
        leaderboard=get_quick_leaderboard(),
        answered=False,
        timed_out=False,
        finished=False
    )


# =========================================================
# ANSWER QUICK SORT
# =========================================================

@app.route("/quick_sort_answer", methods=["POST"])
def quick_sort_answer():
    username = session.get("player")

    if not username:
        return redirect("/")

    item = session.get("quick_item")

    if not item:
        return redirect("/quick_sort")

    if session.get("quick_answered", False):
        return redirect("/quick_sort_next")

    selected_answer = request.form.get("answer")
    correct_answer = item["answer"]
    is_correct = selected_answer == correct_answer

    score = session.get("quick_score", 0)
    correct = session.get("quick_correct", 0)
    total = session.get("quick_total", 0)
    streak = session.get("quick_streak", 0)

    total += 1
    new_best = False

    best_streak = session.get(
        "quick_best_streak",
        0
    )

    if is_correct:
        score += 10
        correct += 1
        streak += 1

        if streak > best_streak:
            best_streak = streak
            new_best = True

    else:
        streak = 0

    session["quick_score"] = score
    session["quick_correct"] = correct
    session["quick_total"] = total
    session["quick_streak"] = streak
    session["quick_best_streak"] = best_streak
    if new_best:
        conn = get_db()
        conn.execute("UPDATE players SET quick_best_streak = MAX(quick_best_streak, ?) WHERE name = ?", (best_streak, username))
        conn.commit()
        conn.close()
    session["quick_answered"] = True

    return render_template(
        "quick_sort.html",
        username=username,
        item=item,
        selected_answer=selected_answer,
        is_correct=is_correct,
        timed_out=False,
        score=score,
        correct=correct,
        total=total,
        streak=streak,
        best_streak=best_streak,
        new_best=new_best,
        leaderboard=get_quick_leaderboard(),
        answered=True,
        finished=False
    )


# =========================================================
# ⏰ QUICK SORT TIMEOUT
# =========================================================

@app.route("/quick_sort_timeout", methods=["POST"])
def quick_sort_timeout():
    username = session.get("player")

    if not username:
        return redirect("/")

    item = session.get("quick_item")

    if not item:
        return redirect("/quick_sort")

    if session.get("quick_answered", False):
        return redirect("/quick_sort_next")

    score = session.get("quick_score", 0)
    correct = session.get("quick_correct", 0)
    total = session.get("quick_total", 0) + 1

    session["quick_total"] = total
    session["quick_streak"] = 0
    session["quick_answered"] = True

    return render_template(
        "quick_sort.html",
        username=username,
        item=item,
        selected_answer=None,
        is_correct=False,
        timed_out=True,
        score=score,
        correct=correct,
        total=total,
        streak=0,
        best_streak=get_quick_best_streak(username),
        new_best=False,
        leaderboard=get_quick_leaderboard(),
        answered=True,
        finished=False
    )


# =========================================================
# NEXT QUICK SORT ITEM
# =========================================================

@app.route("/quick_sort_next")
def quick_sort_next():
    username = session.get("player")
    if not username:
        return redirect("/")

    old_item = session.get("quick_item")
    available_items = [item for item in QUICK_SORT_ITEMS if item != old_item]

    if available_items:
        item = random.choice(available_items)
    else:
        item = random.choice(QUICK_SORT_ITEMS)

    session["quick_item"] = item
    session["quick_answered"] = False

    return render_template(
        "quick_sort.html",
        username=username,
        item=item,
        score=session.get("quick_score", 0),
        correct=session.get("quick_correct", 0),
        total=session.get("quick_total", 0),
        streak=session.get("quick_streak", 0),
        best_streak=session.get("quick_best_streak", 0),
        new_best=False,
        leaderboard=get_quick_leaderboard(),
        answered=False,
        timed_out=False,
        finished=False
    )


# =========================================================
# FINISH QUICK SORT
# =========================================================

@app.route("/quick_sort_finish")
def quick_sort_finish():
    username = session.get("player")

    if not username:
        return redirect("/")

    return render_template(
        "quick_sort.html",
        username=username,
        score=session.get("quick_score", 0),
        correct=session.get("quick_correct", 0),
        total=session.get("quick_total", 0),
        streak=session.get("quick_streak", 0),
        best_streak=session.get("quick_best_streak", 0),
        new_best=False,
        leaderboard=get_quick_leaderboard(),
        finished=True
    )


# =========================================================
# LEADERBOARD
# =========================================================

@app.route(
    "/leaderboard"
)
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

        username=session.get(
            "player"
        )

    )



# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    app.run(

        debug=False,

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )

    )
