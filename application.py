import os
import datetime
import csv

from flask import Flask, redirect, render_template, request, session, url_for, flash
from livereload import Server
from cs50 import SQL
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config.from_pyfile('settings/development.conf')
app.secret_key = os.getenv('SECRET_KEY')

# Configure Heroku Postgres database
db = SQL(os.getenv('DATABASE_URL'))


## Helper Functions ##

# Log error
def log_error(errcode, errmsg):
    time = datetime.datetime.utcnow().isoformat()
    error_pk = db.execute("INSERT INTO errors (errcode, errmsg, created_on) VALUES (:errcode, :errmsg, :time)", \
        errcode=errcode, errmsg=errmsg, time=time)
    
    print(f"error_pk:{error_pk}")

    db.execute("UPDATE users SET last_error=:error_pk WHERE id=:user_id", error_pk=error_pk, user_id=session['user_id'])

# Log feedback
def log_feedback(feedback):
    last_error = db.execute("SELECT last_error FROM users WHERE id=:user_id", user_id=session['user_id'])
    last_error = last_error[0]['last_error']

    db.execute("UPDATE errors SET user_id=:user_id, feedback=:feedback \
                WHERE id=:last_error", user_id=session['user_id'], feedback=feedback, last_error=last_error)




@app.route("/", methods=['GET'])
def index():
    return render_template('index.html')

@app.route("/rules", methods=['GET'])
def rules():
    return render_template('rules.html')

@app.route("/game", methods=['GET'])
def game():
    return render_template('game.html')

@app.route("/character", methods=['GET', 'POST'])
def character():
    if request.method == 'GET':
        return render_template('character.html')

    # On POST
    else:
        charname = request.form.get("name")
        charclass = request.form.get("class")
        strength = request.form.get("strength")
        weakness = request.form.get("weakness")
        ao_1 = request.form.get("ao_1")
        ao_2 = request.form.get("ao_2")
        ao_3 = request.form.get("ao_3")
        lvl_1 = request.form.get("lvl_1")
        lvl_2 = request.form.get("lvl_2")
        lvl_3 = request.form.get("lvl_3")
        lvl_4 = request.form.get("lvl_4")
        print(f"captured:{charname}, {charclass}, {strength}, {weakness}, {ao_1}, {lvl_1}")

        flash(f"Received {charname} stats.")
        return render_template('character.html')



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


@app.route("/admin", methods=['GET'])
def admin_get():
    cards = db.execute("SELECT * FROM cards")
    return render_template('admin.html', cards=cards)   

@app.route("/admin/<task>", methods=['GET', 'POST'])
def admin(task):    

    if request.method == 'GET':
        return render_template('admin.html')


    # On POST
    else:
        print(f'POST task: {task}')

        # Import Templates
        if task == 'import_template':
            foo = request.form.get("filename")
            print(foo)

        if task == 'template_setup':
            with open('static/templates/cards.csv', 'r') as csvfile:

                print('Reading cards.csv...')
                csv_reader = csv.reader(csvfile)

                print('Creating new database...')
                db.execute("CREATE TABLE IF NOT EXISTS cards ( \
                    suit VARCHAR (255), \
                    card VARCHAR (255), \
                    number INTEGER, \
                    symbol VARCHAR (255), \
                    text VARCHAR (4096) \
                    )")

                db.execute("DELETE from cards")

                print('Extracting data...')

                # Skips headers
                next(csv_reader)
                for row in csv_reader:
                    
                    print(f"Adding the {row[1]} of {row[0]}")
                    db.execute("INSERT INTO cards (suit, card, number, symbol, text) VALUES (:suit, :card, :number, :symbol, :text)", \
                                    suit=row[0], card=row[1], number=row[2], symbol=row[3], text=row[4])

                flash(f"Templates setup sucessfully!")

                return redirect('/admin')

        # Setup DB
        if task == 'db_setup':

            # CREATE TABLES

            # users
            db.execute("CREATE TABLE IF NOT EXISTS users ( \
                id serial PRIMARY KEY NOT NULL, \
                username VARCHAR ( 255 ) UNIQUE NOT NULL, \
                password VARCHAR ( 255 ) NOT NULL, \
                created_on TIMESTAMP, \
                last_login TIMESTAMP, \
                last_error INTEGER REFERENCES errors (id) \
                )")

            # cards
                # "primary action, secondary, tertertiary"

            # characters


            # errors
            db.execute("CREATE TABLE IF NOT EXISTS errors ( \
                id serial PRIMARY KEY NOT NULL, \
                errcode INTEGER, \
                errmsg VARCHAR ( 4096 ), \
                created_on TIMESTAMP, \
                user_id integer REFERENCES users (id), \
                feedback VARCHAR ( 4096 ) \
                )")



        flash("Tables Setup!")

        return render_template('admin.html')

# ADMINISTRATIVE #

@app.route("/error", methods=["GET", "POST"])
def error():

    # TODO remove this testing, implement better
    # log_error(errcode, errmsg)
    log_error(418, "I'm a teapot.")

    # log_feedback(user_id, feedback)

    log_feedback(session['user_id'], 'test feedback message')

    return render_template('error.html')



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

        # if username not in authusers:
        #     return render_template("error.html", errcode=403, errmsg="Unauthorized user.")

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

