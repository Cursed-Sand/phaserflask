import os
import psycopg2

from flask import Flask, render_template
from livereload import Server
from cs50 import SQL

app = Flask(__name__)
app.config.from_pyfile('settings/development.conf')


# Configure Heroku Postgres database
db = SQL(os.environ.get('DATABASE_URL').replace("://", "ql://", 1))


@app.route("/", methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == "__main__":
    FLASK_DEBUG=1
    server = Server(app.wsgi_app)
    server.serve()


