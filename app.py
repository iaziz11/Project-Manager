import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, url_for, send_from_directory, abort
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime

UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__)) + '/static/uploads/'

if not os.path.isdir(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
Session(app)

con = sqlite3.connect("data.db", check_same_thread=False)
cur = con.cursor()


def time_format(x):
    """ Changes date-time format from YYYY/MM/DDThh:mm to MM/DD/YYYY hh:mm"""

    x = x.replace("/", "-")
    split = x.split("T")
    date = split[0]
    time = split[1]
    date = date[5:] + "-" + date[:4]
    return date + " " + time


def check_status(deadline, cur_status):
    """Checks the status of a project based on the deadline"""

    # If project status is complete, ignore deadline
    if cur_status == "Complete":
        return "Complete", "green"

    end = datetime(int(deadline[6:10]), int(deadline[0:2]), int(deadline[3:5]), int(deadline[11:13]), int(deadline[14:]))
    now = datetime.now()

    delta = end - now

    if delta.total_seconds() <= 0:
        return "Expired", "red"
    elif delta.total_seconds() < 86400:
        return "Expiring Soon", "#d6a51c"
    else:
        return "Ongoing", "green"


def check_priority(x):
    """Assign colors to priorities"""

    if x == "High":
        return "red"
    elif x == "Medium":
        return "#d6a51c"
    else:
        return "green"


def cur_to_dict_person(x):
    """Converts a cursor object to list of dictionaries"""

    team = []
    for m in x:
            if os.path.exists(os.path.join(UPLOAD_FOLDER, f"{m[0]}.jpg")):
                pfp = os.path.join("/static/uploads", f"{m[0]}.jpg")
            else:
                pfp = os.path.join("/static", "upload_image.png")

            team.append(
                {
                    "id": m[0],
                    "first_name": m[1],
                    "last_name": m[2],
                    "email": m[3],
                    "employee_id": m[4],
                    "pfp": pfp
                }
            )
    return team


def cur_to_dict_project(x):
    """Converts a cursor object to list of dictionaries"""

    projects = []
    for p in x:
        print(p)
        deadline = time_format(p[2])
        created = time_format(p[6])
        status, status_color = check_status(deadline, p[7])
        priority_color = check_priority(p[3])
        projects.append(
            {
                "id": p[0],
                "name": p[1],
                "deadline": deadline,
                "priority": p[3],
                "description": p[4],
                "created": created,
                "status": status,
                "status_color": status_color,
                "priority_color": priority_color
            }
        )
    return projects


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.errorhandler(403)
def page_not_found(e):
    """Handle user trying to access pages not available to them"""

    return render_template('error.html'), 403


@app.errorhandler(404)
def page_not_found(e):
    """Handle user trying to access pages that do not exist"""

    return render_template('error.html'), 404


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


@app.route("/")
@login_required
def index():
    """Index page"""

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    #  Forget any user_id
    session.clear()

    if request.method == "POST":

        #  Ensure username was submitted
        if not request.form.get("username"):
            flash("Please provide username")
            return render_template("login.html")

        #  Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please provide password")
            return render_template("login.html")

        #  Query database for username
        command = cur.execute("""SELECT * FROM users
                              WHERE username = ?""",
                              [request.form.get("username")])
        user = command.fetchone()

        #  Ensure username exists and password is correct
        if user is None:
            flash("Username does not exist")
            return render_template("login.html")

        if not check_password_hash(user[2], request.form.get("password")):
            flash("Incorrect password")
            return render_template("login.html")

        #  Remember which user has logged in
        session["user_id"] = user[0]

        #  Redirect user to projects
        return redirect("/projects")

    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        #  Query database for user
        users = cur.execute("""SELECT * FROM users
                            WHERE username = ?""",
                            [request.form.get("username")])

        #  Check if username has been taken
        if len(users.fetchall()) > 0:
            flash("Username already taken")
            return redirect("/register")

        #  Check if passwords match
        if request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords do not match")
            return redirect("/register")

        #  If user does not exist yet, add them into database
        cur.execute("""INSERT INTO users (username, password)
                    VALUES (?, ?)""",
                    [request.form.get("username"),
                     generate_password_hash(request.form.get("password"))])
        con.commit()

        #  Redirect user to login page
        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget session information
    session.clear()

    # Redirect user to index
    return redirect("/")


@app.route("/projects")
@login_required
def projects():
    """View projects"""

    # Query database for projects that belong to user
    command = cur.execute("""SELECT * FROM project
                          WHERE owner = ?""",
                          [session["user_id"]])

    projects = cur_to_dict_project(command)

    return render_template("projects.html", projects=projects)


@app.route("/team", methods=["GET", "POST"])
@login_required
def team():
    """View team members"""

    if request.method == "GET":

        # Query database for team members that belong to user
        command = cur.execute("""SELECT * FROM person
                              WHERE owner = ?""",
                              [session["user_id"]])

        team = cur_to_dict_person(command)

        return render_template("team.html", team=team)

    # If user wants to view info about a specific team member
    else:

        # Query database for information about a specific user
        member_id = request.form.get("id")
        command = cur.execute("""SELECT * FROM person
                              WHERE owner = ?
                              AND id = ?""",
                              [session["user_id"],
                               member_id])

        employee = cur_to_dict_person(command)

        # Check if user tries to access information that does not exist
        if len(employee) == 0:
            abort(404)

        return redirect("/viewmember", p=employee[0])


@app.route("/addmember", methods=["GET", "POST"])
@login_required
def add_member():
    """Add team member"""

    if request.method == "POST":

        # Add new team member into the database
        cur.execute("""INSERT INTO person (first_name, last_name, email, employee_id, owner)
                    VALUES (?, ?, ?, ?, ?)""",
                    [request.form.get("first_name"),
                     request.form.get("last_name"),
                     request.form.get("email"),
                     request.form.get("employee_id"),
                     session["user_id"]])
        con.commit()

        # Check if user uploaded a profile picture
        # https://viveksb007.github.io/2018/04/uploading-processing-downloading-files-in-flask
        if 'pfpupload' not in request.files:
            return redirect("/team")

        file = request.files['pfpupload']
        if file.filename == '':
            return redirect("/team")

        # Save picture to static/uploads
        filename = f"{cur.lastrowid}.jpg"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect("/team")

    else:
        return render_template("add_member.html")


@app.route("/addproject", methods=["GET", "POST"])
@login_required
def add_project():
    """Add project"""

    if request.method == "POST":

        # Add new project into the database
        cur.execute("""INSERT INTO project (name, deadline, created, priority, description, owner, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    [request.form.get("project_name"),
                     request.form.get("deadline"),
                     datetime.now().strftime("%Y/%m/%dT%H:%M"),
                     request.form.get("priority"),
                     request.form.get("description"),
                     session["user_id"],
                     "Active"])
        con.commit()
        project_id = cur.lastrowid

        # Associate team members to project
        for m in request.form.getlist("team_members"):
            cur.execute("""INSERT INTO association (project_id, person_id)
                        VALUES (?, ?)""",
                        [project_id,
                         m])
            con.commit()

        return redirect("/projects")

    else:

        # Query database for team members
        command = cur.execute("""SELECT * FROM person
                              WHERE owner = ?""",
                              [session["user_id"]])

        team = cur_to_dict_person(command)

        # Do not allow user to create a project if no team members exist
        if len(team) == 0:
            flash("You need at least one team member to create a project")
            return redirect("/projects")

        return render_template("add_project.html", team=team)


@app.route("/viewmember", methods=["GET", "POST"])
@login_required
def view_member():
    """View team member"""

    # User wants to remove a team member
    if request.method == "POST":

        user_id = request.form.get("delete")
        filename = f"{user_id}.jpg"

        # Remove team member from database
        cur.execute("""DELETE FROM person
                    WHERE id = ?
                    AND owner = ?""",
                    [user_id,
                     session['user_id']])
        con.commit()

        # Delete user's profile picture if they have one
        if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
            os.remove(os.path.join(UPLOAD_FOLDER, filename))

        flash("Team Member Removed")
        return redirect("/team")

    # User wants to view profile of a team member
    else:

        user_id = request.args.get("id")
        filename = f"uploads/{user_id}.jpg"

        # Query database for user matching id
        command = cur.execute("""SELECT * FROM person
                              WHERE owner = ?
                              AND id = ?""",
                              [session["user_id"],
                               user_id])

        employee = cur_to_dict_person(command)

        # Check if user tries to access information not available to them
        if len(employee) == 0:
            abort(403)

        return render_template("view_member.html", p=employee[0], pfp=filename)


@app.route("/viewproject", methods=["GET", "POST"])
@login_required
def view_project():

    """View project"""

    # User wants to mark a project as completed or remove a project
    if request.method == "POST":

        # Mark project as completed
        if request.form.get("complete"):
            cur.execute("""UPDATE project SET status = ?
                        WHERE id = ?""",
                        ["Complete",
                         request.form.get('complete')])
            con.commit()

            flash("Project Completed")
            return redirect("/projects")

        # Delete project from database
        elif request.form.get("delete"):
            cur.execute("""DELETE FROM project
                        WHERE id = ?
                        AND owner = ?""",
                        [request.form.get('delete'),
                         session['user_id']])
            con.commit()

            flash("Project Deleted")
            return redirect("/projects")

        return redirect("/projects")

    # User wants to view details of a project
    else:

        project_id = request.args.get("id")

        # Query the database for the project that is requested
        command1 = cur.execute("""SELECT * FROM project
                               WHERE owner = ?
                               AND id = ?""",
                               [session["user_id"],
                                project_id])

        project = cur_to_dict_project(command1)

        # Query the database for the team that is working on the project
        command2 = cur.execute("""SELECT * FROM person
                               WHERE id IN (SELECT id FROM person
                               JOIN association ON person.id = association.person_id
                               WHERE association.project_id = ?
                               AND person.owner = ?)""",
                               [project_id,
                                session["user_id"]])

        team = cur_to_dict_person(command2)

        # Check if user tries to access information not available to them
        if len(project) == 0:
            abort(403)

        return render_template("view_project.html", team=team, p=project[0])
    

if __name__ == '__main__':
    app.run()