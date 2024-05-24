from flask import Flask
from db import DB
app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"