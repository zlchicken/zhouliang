from info.models import User
from . import index_blu
from flask import render_template, session


@index_blu.route("/")
def index():
    if 'id' in session:
        user_id = session["id"]

        user = User.query.filter_by(id=user_id).first()
        data = {
            "user": user
        }
        return render_template("news/index.html", data=data)
    else:
        data = {
        }
        return render_template("news/index.html", data=data)