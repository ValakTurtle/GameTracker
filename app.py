import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for
from database import get_connection, create_table
import json
import os
from datetime import datetime, timedelta

with open("json/dropdowns.json") as f:
    dropdown_data = json.load(f)

PLATFORM_GROUPS = dropdown_data["platformGroups"]
STATUSES = dropdown_data["statuses"]

app = Flask(__name__)

create_table()

def update_playing_to_on_hold():
    """Check all games currently 'Playing' and if started >21 days ago, move to 'On Hold'."""
    conn = get_connection()
    now = datetime.now()
    three_weeks_ago = now - timedelta(days=21)

    # Fetch games with status 'Playing' and a start_play_date older than 21 days
    games_to_hold = conn.execute("""
        SELECT id, start_play_date FROM games
        WHERE status = 'Playing' AND start_play_date IS NOT NULL
    """).fetchall()

    for game in games_to_hold:
        start_play_date_str = game["start_play_date"]
        if start_play_date_str:
            try:
                start_play_date = datetime.strptime(start_play_date_str, "%Y-%m-%d")
                if start_play_date <= three_weeks_ago:
                    # Update status to 'On Hold', keep status_change_date current
                    conn.execute("""
                        UPDATE games
                        SET status = 'On Hold',
                            status_change_date = ?
                        WHERE id = ?
                    """, (now.strftime("%Y-%m-%d"), game["id"]))
            except Exception as e:
                print(f"Error parsing date for game id {game['id']}: {e}")

    conn.commit()
    conn.close()


@app.route("/")
def home():
    update_playing_to_on_hold()

    conn = get_connection()
    all_games = conn.execute("SELECT * FROM games").fetchall()
    conn.close()

    # group by status
    grouped_games = {
        "Playing": [],
        "On Hold": [],
        "Not Started": [],
        "Completed": [],
    }

    for game in all_games:
        status = game["status"]
        if status in grouped_games:
            grouped_games[status].append(game)

    return render_template("home.html", grouped_games=grouped_games)


@app.route("/add", methods=["GET", "POST"])
def add_game():
    if request.method == "POST":
        title = request.form.get("title")
        platforms = request.form.getlist("platforms")
        platform_str = ",".join(platforms)
        status = request.form.get("status")
        rating = request.form.get("rating")
        cover_url = request.form.get("cover_url")
        notes = request.form.get("notes")

        # check required fields
        if not title or not status or not platforms:
            return "Title, status, and at least one platform are required.", 400

        now_str = datetime.now().strftime("%Y-%m-%d")

        # status_change_date always now
        status_change_date = now_str

        # handle start_play_date and start_date
        if status == "Playing":
            start_play_date = now_str
            start_date = now_str
            finish_date = None
        elif status == "Completed":
            start_play_date = None  # in case they skipped Playing status
            start_date = None
            finish_date = now_str
        else:
            start_play_date = None
            start_date = None
            finish_date = None

        conn = get_connection()
        conn.execute("""
            INSERT INTO games (title, platform, status, rating, cover_url, notes, start_date, finish_date, status_change_date, start_play_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            platform_str,
            status,
            rating,
            cover_url,
            notes,
            start_date,
            finish_date,
            status_change_date,
            start_play_date,
        ))
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

        now_str = datetime.now().strftime("%Y-%m-%d")

        # Prepare update params
        params = [title, platform_str, status, rating, cover_url, notes, start_date, finish_date]

        # Logic to update status_change_date and start_play_date if status changed:
        if status != game["status"]:
            params.append(now_str)  # status_change_date = now

            # If changed to Playing, always reset start_play_date to now
            if status == "Playing":
                params.append(now_str)
            else:
                # for other statuses, keep the existing start_play_date
                params.append(game["start_play_date"])
        else:
            # No status change: keep existing dates
            params.append(game["status_change_date"])
            params.append(game["start_play_date"])

        params.append(game_id)  # for WHERE clause

        conn.execute("""
            UPDATE games
            SET title=?, platform=?, status=?, rating=?, cover_url=?, notes=?, start_date=?, finish_date=?,
                status_change_date=?, start_play_date=?
            WHERE id=?
        """, params)

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
        statuses=STATUSES,
        selected_platforms=selected_platforms  # pass for preselect
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



# Have an option for list mode or grid mode
    # Make the Cover Image URL work
    # Remove game rating?
# Have the games be sorted in alphabetical order (or maybe by start_date for Playing?)
# Remove Start Date and Finish Date sections in Add Game page, will have that stuff be automatic