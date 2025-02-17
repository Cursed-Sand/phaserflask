import os
import datetime
import csv

from flask import Flask, redirect, render_template, request, session, url_for, flash
from livereload import Server
from cs50 import SQL
from functools import wraps
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config.from_pyfile('settings/development.conf')
app.secret_key = os.getenv('SECRET_KEY')

# Configure Heroku Postgres database
db = SQL(os.getenv('DATABASE_URL'))


## Helper Functions ##

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Require login to a route
def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/welcome")
        return f(*args, **kwargs)
    return decorated_function

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


@app.route("/", methods=['GET', 'POST'])
@login_required
def index():

    if request.method == 'GET':
        username = db.execute("SELECT username FROM users WHERE id=:id", id=session['user_id'])

        friends = db.execute("SELECT username FROM users WHERE \
                                id=(SELECT inviter FROM friends WHERE accept='true' AND invitee=:id) \
                                OR \
                                id=(SELECT invitee FROM friends WHERE accept='true' AND inviter=:id) \
                                ", id=session['user_id'])
        print(f"friends:{friends}")

        invitations = db.execute("SELECT id, username FROM users WHERE \
                                id=(SELECT inviter FROM friends WHERE blocked!='true' AND accept='false' AND invitee=:id) \
                                OR \
                                id=(SELECT invitee FROM friends WHERE blocked!='true' AND accept='true' AND inviter=:id) \
                                ", id=session['user_id'])
        print(f"invitations:{invitations}")

        print(friends)

        campaigns = db.execute("SELECT * FROM campaigns where \
                                id=(SELECT campaign_id FROM parties WHERE user_id=:id) \
                                ", id=session['user_id'])

        return render_template('index.html', username=username[0], friends=friends, campaigns=campaigns, invitations=invitations)

    else:

        return "testing"

@app.route("/welcome", methods=['GET'])
def welcome():
    return render_template('welcome.html')

@app.route("/rules", methods=['GET'])
def rules():
    cards = db.execute("SELECT * FROM cards")
    classes = db.execute("SELECT * FROM classes")
    return render_template('rules.html', cards=cards, classes=classes)

@app.route("/pregame", methods=['GET'])
@login_required
def pregame():
    classes = db.execute("SELECT * FROM classes")
    return render_template('pregame.html', classes=classes)

@app.route("/game", methods=['GET'])
@login_required
def game():
    return render_template('game.html')

@app.route("/phaser", methods=['GET'])
@login_required
def phaser():
    return render_template('phaser.html')

@app.route("/character", methods=['GET', 'POST'])
@login_required
def character():
    if request.method == 'GET':
        characters = db.execute("SELECT * FROM characters")
        abilities = db.execute("SELECT * FROM abilities")
        classes = db.execute("SELECT * FROM classes")

        return render_template('character.html', characters=characters, abilities=abilities, classes=classes)

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

        db.execute("INSERT INTO characters (name) VALUES (:name)", name=charname)

        flash(f"Added {charname} into database.")
        characters = db.execute("SELECT * FROM characters")
        abilities = db.execute("SELECT * FROM abilities")
        classes = db.execute("SELECT * FROM classes")

        return render_template('character.html', characters=characters, abilities=abilities, classes=classes)

@app.route("/settings", methods=['GET'])
@login_required
def settings_get():
    return render_template('settings.html')   

@app.route("/admin", methods=['GET'])
@login_required
def admin_get():
    cards = db.execute("SELECT * FROM cards")
    return render_template('admin.html', cards=cards)   

@app.route("/admin/<task>", methods=['GET', 'POST'])
@login_required
def admin(task):    

    if request.method == 'GET':
        return render_template('admin.html')

    # On POST
    else:
        print(f'POST task: {task}')

        # Add friend
        if task == 'invite_friend':
            friendname = request.form.get("friendname")
            match = db.execute("SELECT id, username FROM users WHERE username=:friendname", friendname=friendname)

            # Ensure invited user exists
            if not match:
                flash(f"No such username: {friendname}")
                return redirect("/")
            
            # Outgoing relationship
            relationship = db.execute("SELECT * FROM friends WHERE inviter=:id AND invitee= \
                                    (SELECT id FROM users WHERE username=:friendname)", id=session['user_id'], friendname=friendname)
            
            # Incoming relationship
            inrelationship = db.execute("SELECT * FROM friends WHERE invitee=:id AND inviter= \
                                    (SELECT id FROM users WHERE username=:friendname)", id=session['user_id'], friendname=friendname)

            # If inviting someone who has already invited you, just accept their request
            if inrelationship:
                db.execute("UPDATE friends SET accept='true' AND blocked='false' WHERE id=:friend_id", \
                                friend_id=inrelationship[0]['id'])
                flash(f"Accepted existing friend invitation from {friendname}.")
                return redirect("/")

            # Is the inviter already blocked by invitee?
            if relationship[0]['blocked'] is True:
                # Inviting a user that has blocked inviter returns result as if the invitee does not exist
                flash(f"No such username: {friendname}")
                return redirect("/")

            # Prevent duplicate invitations
            if len(relationship) > 0:
                flash(f"Invitation already sent to {friendname}.")
                return redirect ("/")

            # Add the invitation
            if len(relationship) == 0:
                db.execute("INSERT INTO friends (inviter, invitee, accept) VALUES (:id, :invitee, 'false')", \
                            id=session['user_id'], invitee=match[0]['id'])
                flash(f"Invitation has been sent to {friendname}.")
                return redirect ("/")

            else:
                flash("Unexpected error.")
                return redirect ("/")

        # Accept friend
        if task == 'accept_friend':
            return 'test'

        # Block friend
        if task == 'block_friend':
            return 'test'

        # Add campaign
        if task == 'add_campaign':
            return 'test'

        # Import Templates
        # TODO get file import working
        if task == 'import_template':
            foo = request.form.get("filename")
            print(foo)

        # Card & class template setup
        if task == 'template_setup':

            # CARDS
            with open('static/templates/cards.csv', 'r') as csvfile:

                print('Reading cards.csv...')
                csv_reader = csv.reader(csvfile)

                print('Creating new database...')
                db.execute("CREATE TABLE IF NOT EXISTS cards ( \
                    suit VARCHAR (255), \
                    card VARCHAR (255), \
                    number INTEGER, \
                    symbol VARCHAR (255), \
                    text VARCHAR (4096), \
                    location VARCHAR (4096), \
                    encounter VARCHAR (4096), \
                    object VARCHAR (4096) \
                    )")

                db.execute("DELETE from cards")

                print('Extracting data...')

                # Skips headers
                next(csv_reader)
                for row in csv_reader:
                    
                    print(f"Adding the {row[1]} of {row[0]}")
                    db.execute("INSERT INTO cards (suit, card, number, symbol, text, location, encounter, object) \
                                VALUES (:suit, :card, :number, :symbol, :text, :location, :encounter, :object)", \
                                    suit=row[0], card=row[1], number=row[2], symbol=row[3], text=row[4], location=row[5], encounter=row[6], object=row[7])


            # CLASSES
            with open('static/templates/classes.csv', 'r') as csvfile:

                print('Reading classes.csv...')
                csv_reader = csv.reader(csvfile)

                print('Creating new database...')

                # classes
                db.execute("CREATE TABLE IF NOT EXISTS classes ( \
                    id serial PRIMARY KEY NOT NULL, \
                    name VARCHAR ( 255 ), \
                    description VARCHAR ( 255 ) \
                )")
                
                db.execute("DELETE from classes")

                print('Extracting data...')

                # Skips headers
                next(csv_reader)
                for row in csv_reader:
                    
                    print(f"Adding the {row[0]} class...")
                    db.execute("INSERT INTO classes (name, description) \
                                VALUES (:name, :description)", \
                                name=row[0], description=row[1])

            flash(f"Templates setup sucessfully!")

            return redirect('/admin')

        #### CREATE TABLES ####
        if task == 'db_setup':

            ## ADMIN ##

            # errors
            db.execute("CREATE TABLE IF NOT EXISTS errors ( \
                id serial PRIMARY KEY NOT NULL, \
                errcode INTEGER, \
                errmsg VARCHAR ( 4096 ), \
                created_on TIMESTAMP, \
                user_id integer REFERENCES users (id), \
                feedback VARCHAR ( 4096 ) \
                )")

            # users
            db.execute("CREATE TABLE IF NOT EXISTS users ( \
                id serial PRIMARY KEY NOT NULL, \
                username VARCHAR ( 255 ) UNIQUE NOT NULL, \
                password VARCHAR ( 255 ) NOT NULL, \
                created_on TIMESTAMP, \
                last_login TIMESTAMP, \
                last_error INTEGER REFERENCES errors ( id ), \
                campaign_id INTEGER REFERENCES campaigns ( id ) \
                )")

            # friends
            db.execute("CREATE TABLE IF NOT EXISTS friends ( \
                id serial PRIMARY KEY NOT NULL, \
                inviter INTEGER REFERENCES users ( id ), \
                invitee INTEGER REFERENCES users ( id ), \
                accept BOOL, \
                blocked BOOL \
                )")

            ## GAME ##

            # campaigns
            # status = (pregame || game || archive)
            db.execute("CREATE TABLE IF NOT EXISTS campaigns ( \
                id serial PRIMARY KEY NOT NULL, \
                name VARCHAR ( 255 ), \
                status VARCHAR ( 255 ) \
                )")

            # parties
            db.execute("CREATE TABLE IF NOT EXISTS parties ( \
                id serial PRIMARY KEY NOT NULL, \
                campaign_id INTEGER REFERENCES campaigns ( id ), \
                user_id INTEGER REFERENCES users ( id ) \
                )")

            # classes
            db.execute("CREATE TABLE IF NOT EXISTS classes ( \
                id serial PRIMARY KEY NOT NULL, \
                name VARCHAR ( 255 ), \
                description VARCHAR ( 255 ) \
                )")

            # abilities
            db.execute("CREATE TABLE IF NOT EXISTS abilities ( \
                id serial PRIMARY KEY NOT NULL, \
                name VARCHAR ( 255 ), \
                description VARCHAR ( 255 ) \
                )")

            # locations
            db.execute("CREATE TABLE IF NOT EXISTS locations ( \
                id serial PRIMARY KEY NOT NULL, \
                name VARCHAR ( 255 ), \
                description VARCHAR ( 255 ) \
                )")

            # encounters
            db.execute("CREATE TABLE IF NOT EXISTS encounters ( \
                id serial PRIMARY KEY NOT NULL, \
                name VARCHAR ( 255 ), \
                description VARCHAR ( 255 ) \
                )")

            # objects
            db.execute("CREATE TABLE IF NOT EXISTS objects ( \
                id serial PRIMARY KEY NOT NULL, \
                name VARCHAR ( 255 ), \
                effect VARCHAR ( 255 ) \
                )")

            # characters
            db.execute("CREATE TABLE IF NOT EXISTS characters ( \
                id serial PRIMARY KEY NOT NULL, \
                campaign INTEGER REFERENCES campaigns ( id ), \
                name VARCHAR ( 255 ), \
                class VARCHAR ( 255 ), \
                strength VARCHAR ( 255 ), \
                weakness VARCHAR ( 255 ), \
                ability_1 INTEGER REFERENCES abilities ( id ), \
                ability_2 INTEGER REFERENCES abilities ( id ), \
                ability_3 INTEGER REFERENCES abilities ( id ), \
                ability_4 INTEGER REFERENCES abilities ( id ), \
                ao_1 INTEGER REFERENCES objects ( id ), \
                ao_2 INTEGER REFERENCES objects ( id ), \
                ao_3 INTEGER REFERENCES objects ( id ) \
                )")

            # actions
            db.execute("CREATE TABLE IF NOT EXISTS actions ( \
                id serial PRIMARY KEY NOT NULL, \
                name VARCHAR ( 255 ), \
                description VARCHAR ( 4096 ) \
                )")                

            # logs
            db.execute("CREATE TABLE IF NOT EXISTS logs ( \
                id serial PRIMARY KEY NOT NULL, \
                campaign_id INTEGER REFERENCES campaigns ( id ), \
                actor_character_id INTEGER REFERENCES characters ( id ), \
                action_id INTEGER REFERENCES actions ( id ), \
                object_id INTEGER, \
                time TIMESTAMP \
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
        # TODO cantrip


    # Abilities (52+2)
        # id
        # name
        # description
        # pulled/drawn


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
    return redirect("/welcome")


if __name__ == "__main__":
    server = Server(app.wsgi_app)
    server.serve()

