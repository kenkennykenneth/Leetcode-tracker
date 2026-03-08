from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from functools import wraps
#Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process (grants permission to run python in my virtual environment)

app = Flask(__name__)
app.secret_key = "super_duper_mega_hidden_security_key"

#  # 1. Get the folder where THIS python file is located
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # 2. Force the database to live in that same folder
# 'leetcode3.db' = os.path.join(BASE_DIR, 'leetcode.db')

def init_db():
    conn = sqlite3.connect('leetcode3.db')
    pen = conn.cursor()
    pen.execute('''
        CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        time_taken INTEGER,
        date_added TEXT
        );
''')
    
    pen.execute('''
        CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        hash TEXT NOT NULL
        );
''')
    
    conn.commit()
    conn.close()

init_db()

DIFFICULTY = ["HARD", "MEDIUM", "EASY"]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session["user_ID"]
        if user_id is None:
            return redirect("/login")
        
        conn = sqlite3.connect('leetcode3.db')
        pen = conn.cursor()
        user_exists = pen.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user_exists:
            session.clear()
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    return render_template("home.html")

@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session.get("user_ID")
    conn = sqlite3.connect('leetcode3.db')
    pen = conn.cursor()
    name = pen.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template("dashboard.html", name = name[0])

@app.route('/add', methods=["GET", "POST"])
@login_required
def add_problem():
    user_id = session["user_ID"]
    if request.method == "POST":
        problem_name = request.form.get("problem_name")
        difficulty = request.form.get("difficulty")
        raw_time_taken = request.form.get("time-taken")
        date = request.form.get("date-added")

        if not problem_name:
            flash("Missing problem name")
            return redirect("/add")
        if not difficulty:
            flash("Missing difficulty")
            return redirect("/add")
        if not date:
            flash("Date field required")
            return redirect("/add")
        if not raw_time_taken:
            flash("Time field required")
            return redirect("/add")
        if difficulty not in DIFFICULTY:
            flash("Difficulty not found")
            return redirect("/add")
        
        # change the time to minutes and integer (it was given in string e.g 01:30)
        time_split = raw_time_taken.split(":")
        hours = int(time_split[0])
        minutes = int(time_split[1])
        total_time_minutes = (hours * 60) + minutes
        
        conn = sqlite3.connect('leetcode3.db')
        pen = conn.cursor()
        command = "INSERT INTO problems (name, difficulty, time_taken, date_added, user_ID) VALUES (?, ?, ?, ?, ?)"
        pen.execute(command, (problem_name, difficulty, total_time_minutes, date, user_id))
        conn.commit()
        conn.close()
        return redirect("/history")
    return render_template("add.html", difficulties = DIFFICULTY)


@app.route('/history', methods=["POST", "GET"])
@login_required
def show():
    user_id = session["user_ID"]
    conn = sqlite3.connect('leetcode3.db')
    pen = conn.cursor()
    command = "SELECT * FROM problems WHERE user_ID = ?"
    data = pen.execute(command, (user_id,)).fetchall()
    conn.close()
    return render_template("show.html", problem_data = data)

@app.route('/stats')
def stats():
    user_id = session["user_ID"]
    conn = sqlite3.connect('leetcode3.db')
    pen = conn.cursor()
    total_result = pen.execute('SELECT COUNT(*) FROM problems WHERE user_ID = ?', (user_id,)).fetchone()
    TOTAL = str(total_result[0])

    ROWS = pen.execute('SELECT difficulty, COUNT(*) FROM problems WHERE user_ID = ? GROUP BY difficulty', (user_id,)).fetchall()

    conn.close()
    return render_template("stats.html", total = TOTAL, rows = ROWS)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username(html)")
        password = request.form.get("password(html)")
        confirmation = request.form.get("confirmation(html)")

        if not username or not password or not confirmation:
            flash("All fields are required")
            return render_template("register.html")
        
        if password != confirmation:
            flash("Passwords do not match")
            return render_template("register.html")
        
        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect('leetcode3.db')
        pen = conn.cursor()

        try:
            pen.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            
        except sqlite3.IntegrityError:
            flash("Username taken!")
            return render_template("register.html")
        
        finally:
            conn.close()
        
        return redirect('/login')
        
    return render_template("register.html")


@app.route('/login', methods=["POST", "GET"])
def login():
    if "user_ID" in session:
        return redirect('/dashboard')
    
    else:
        session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Both fields are required")
            return render_template("login.html")
        
        conn = sqlite3.connect('leetcode3.db')
        pen = conn.cursor()
        command = "SELECT * FROM users WHERE username = ?"
        login_details = pen.execute(command, (username,)).fetchone()
        conn.close()

        if login_details == None or check_password_hash(login_details[2], password) == False:
            flash("Invalid username and/or password")
            return render_template("login.html")
        
        session["user_ID"] = login_details[0]

        return redirect('/dashboard')
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/delete_specific/<int:problem_id>", methods=['POST', 'GET'])
def delete_specific(problem_id):
    if request.method == "POST":
        user = session.get("user_ID")
        conn = sqlite3.connect('leetcode3.db')
        pen = conn.cursor()
        command = "DELETE FROM problems WHERE id = ? AND user_ID = ?"
        pen.execute(command, (problem_id, user))
        conn.commit()
        conn.close()
    return redirect("/history")

@app.route("/delete_all", methods=["POST", "GET"])
def delete_all():
    if request.method == "POST":
        user = session.get("user_ID")
        conn = sqlite3.connect('leetcode3.db')
        pen = conn.cursor()
        pen.execute("DELETE FROM problem WHERE user_ID = ?", (user,))
    return redirect('/history')
    
if __name__ == "__main__":
    app.run(debug = True)
