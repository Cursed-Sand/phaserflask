import os
import psycopg2

from flask import Flask, render_template
from livereload import Server
from cs50 import SQL

app = Flask(__name__)
app.config.from_pyfile('settings/development.conf')


# Configure Heroku Postgres database
db = SQL(os.getenv('DATABASE_URL'))


@app.route("/", methods=['GET'])
def index():
    return render_template('index.html')


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




if __name__ == "__main__":
    FLASK_DEBUG=1
    server = Server(app.wsgi_app)
    server.serve()

