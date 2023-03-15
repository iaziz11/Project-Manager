import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# con = sqlite3.connect("data.db")
# cur = con.cursor()
# cur.execute("""CREATE TABLE IF NOT EXISTS person (
#                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
#                name TEXT,
#                phone_number VARCHAR[10]
# )""")

# cur.execute("""INSERT INTO person (name, phone_number) VALUES
#                (?, ?)""", ("Bobby", "1234567890"))
# con.commit()

@app.route("/")
#@login_required
def index():
    """Index redirects to projects"""

    return redirect("/projects")


@app.route("/projects")
#@login_required
def projects():
    """View projects"""

    p = [{
        "name": "test1",
        "start_time": "1",
        "end_time": "2",
        "status": "ongoing",
        "priority": "high"
    },{
        "name": "test2",
        "start_time": "5",
        "end_time": "8",
        "status": "expired",
        "priority": "low"
    }]
    if request.method == "GET":
        return render_template("projects.html", projects=p)


@app.route("/team", methods=["GET", "POST"])
#@login_required
def team():
    """View projects"""

    p = [{
        "first_name": "ABC",
        "last_name": "CBA",
        "employee_id": "289389",
        "email": "abc@gmail.com",
    },{
        "first_name": "XYZ",
        "last_name": "ZYX",
        "employee_id": "4839849",
        "email": "xyz@gmail.com",
    }]
    if request.method == "GET":
        return render_template("team.html", team=p)
    else:
        print("View team member")
        return render_template("team.html", team=p)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        
        #  Query database for user
        users = cur.execute("""SELECT * FROM users
                            WHERE username = ?""",
                            request.form.get("username"))

        #  Check if username has been taken
        if len(users) > 0:
            flash("Username already taken")
            return redirect("/register")

        #  Check if passwords match
        if request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords do not match")
            return redirect("/register")

        #  If user does not exist yet, add them into database
        cur.execute("""INSERT INTO users (username, hash)
                    VALUES (?, ?)""",
                    request.form.get("username"),
                    generate_password_hash(request.form.get("password")))

        #  Redirect user to home page
        return redirect("/")
    
    else:

        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    #  Forget any user_id
    session.clear()

    if request.method == "POST":

        #  Ensure username was submitted
        if not request.form.get("username"):
            flash("Please provide username")
            return redirect("/login")

        #  Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please provide password")
            return redirect("/login")

        #  Query database for username
        rows = cur.execute("""SELECT * FROM users
                           WHERE username = ?""",
                           request.form.get("username"))

        #  Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password")
            return redirect("/login")

        #  Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        #  Redirect user to home page
        return redirect("/")

    else:

        return render_template("login.html")


@app.route("/addmember", methods=["GET", "POST"])
#@login_required
def add_member():
    """Add team member"""

    return render_template("add_member.html")

@app.route("/addproject", methods=["GET", "POST"])
#@login_required
def add_project():
    """Add project"""

    return render_template("add_project.html")
