import os
# import psycopg2

from flask import Flask, redirect, render_template, request, session, url_for, flash
from livereload import Server
from cs50 import SQL

app = Flask(__name__)
app.config.from_pyfile('settings/development.conf')
app.secret_key = os.getenv('SECRET_KEY')

# Configure Heroku Postgres database
db = SQL(os.getenv('DATABASE_URL'))


@app.route("/", methods=['GET'])
def index():
    return render_template('layout.html')

@app.route("/summary", methods=['GET'])
def summary():
    return render_template('summary.html')


@app.route("/test", methods=['GET'])
def test():

    # CREATE TABLES
    # Users
    db.execute("CREATE TABLE IF NOT EXISTS users ( \
        id serial PRIMARY KEY NOT NULL, \
        username VARCHAR ( 255 ) UNIQUE NOT NULL, \
        password VARCHAR ( 255 ) NOT NULL, \
        created_on TIMESTAMP, \
        last_login TIMESTAMP \
        )")

    # Characters
        # id
        # name
        # description
        #         

    # Classes
        # id
        # name
        # description
        # cantrip


    # Abilities (52+2)
        # id
        # name
        # description
        # pulled/drawn        


    return 'HELLO TEST'

@app.route("/db", methods=['GET'])
def db():
    
    return 'HELLO db'



# ADMINISTRATIVE #

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Serve registration page
    if request.method == 'GET':
        return render_template("register.html")

    # Process submitted form responses on POST
    else:

        # Error Checking
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", errcode=403, errmsg="Username required.")

        # Ensure password was submitted
        if not request.form.get("password"):
            return render_template("error.html", errcode=403, errmsg="Password required.")

        # Ensure password and password confirmation match
        if request.form.get("password") != request.form.get("passwordconfirm"):
            return render_template("error.html", errcode=403, errmsg="Passwords must match.")

        # Ensure minimum password length
        if len(request.form.get("password")) < 8:
            return render_template("error.html", errcode=403, errmsg="Password must be at least 8 characters.")

        # Store the hashed username and password
        username = request.form.get("username")
        hashedpass = generate_password_hash(request.form.get("password"))

        if username not in authusers:
            return render_template("error.html", errcode=403, errmsg="Unauthorized user.")

        # Check if username is already taken
        if not db.execute("SELECT username FROM users WHERE username LIKE (?)", username):

            # Add the username
            time = datetime.datetime.utcnow().isoformat()
            db.execute("INSERT INTO users (username, password, created_on) VALUES (:username, :hashedpass, :time)",
                        username=username, hashedpass=hashedpass, time=time)
            return redirect("/")

        else:
            return render_template("error.html", errcode=403, errmsg="Username invalid or already taken.")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", errcode=400, errmsg="Username required.")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", errcode=400, errmsg="Password required.")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists
        if len(rows) != 1:
            return render_template("register.html", errmsg="Username not found.")

        # Ensure username exists and password is correct
        if not check_password_hash(rows[0]["password"], request.form.get("password")):
            return render_template("error.html", errcode=403, errmsg="Incorrect password.")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Update "last_login"
        time = datetime.datetime.utcnow().isoformat()
        db.execute("UPDATE users SET last_login=:time WHERE id=:id", time=time, id=session["user_id"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

   # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



if __name__ == "__main__":
    server = Server(app.wsgi_app)
    server.serve()

