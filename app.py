import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for
from database import get_connection, create_table
import json
import os

with open("json/dropdowns.json") as f:
    dropdown_data = json.load(f)

PLATFORM_GROUPS = dropdown_data["platformGroups"]
STATUSES = dropdown_data["statuses"]

app = Flask(__name__)

create_table()

@app.route("/")
def home():
    conn = get_connection()
    games = conn.execute("SELECT * FROM games").fetchall()
    conn.close()
    return render_template("home.html", games=games)

@app.route("/add", methods=["GET", "POST"])
def add_game():
    if request.method == "POST":
        title = request.form.get("title")
        platforms = request.form.getlist("platforms")  # multi-select
        platform_str = ",".join(platforms)
        status = request.form.get("status")
        rating = request.form.get("rating")
        cover_url = request.form.get("cover_url")
        notes = request.form.get("notes")
        start_date = request.form.get("start_date")
        finish_date = request.form.get("finish_date")

        conn = get_connection()
        conn.execute("""
            INSERT INTO games (title, platform, status, rating, cover_url, notes, start_date, finish_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, platform_str, status, rating, cover_url, notes, start_date, finish_date))
        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return render_template(
        "game_form.html",
        game=None,
        form_action=url_for("add_game"),
        submit_text="Add Game",
        platform_groups=PLATFORM_GROUPS,
        statuses=STATUSES
    )


@app.route("/edit/<int:game_id>", methods=["GET", "POST"])
def edit_game(game_id):
    conn = get_connection()
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if game is None:
        conn.close()
        return "Game not found!", 404

    if request.method == "POST":
        title = request.form.get("title")
        platforms = request.form.getlist("platforms")
        platform_str = ",".join(platforms)
        status = request.form.get("status")
        rating = request.form.get("rating")
        cover_url = request.form.get("cover_url")
        notes = request.form.get("notes")
        start_date = request.form.get("start_date")
        finish_date = request.form.get("finish_date")

        conn.execute("""
            UPDATE games
            SET title=?, platform=?, status=?, rating=?, cover_url=?, notes=?, start_date=?, finish_date=?
            WHERE id=?
        """, (title, platform_str, status, rating, cover_url, notes, start_date, finish_date, game_id))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    # split platforms for preselect
    selected_platforms = []
    if game["platform"]:
        selected_platforms = game["platform"].split(",")

    conn.close()
    return render_template(
        "game_form.html",
        game=game,
        form_action=url_for("edit_game", game_id=game_id),
        submit_text="Save Changes",
        platform_groups=PLATFORM_GROUPS,
        statuses=STATUSES
    )


@app.route("/delete/<int:game_id>", methods=["POST"])
def delete_game(game_id):
    conn = get_connection()
    conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

if __name__ == "__main__":
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        Timer(1, open_browser).start()
    app.run(debug=True)
