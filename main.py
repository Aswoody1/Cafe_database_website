from flask import Flask, jsonify, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from werkzeug.utils import redirect
from wtforms import StringField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, URL
import random
import requests
import os

SECRET_KEY = os.urandom(32)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

##Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.app_context().push()

Bootstrap(app)
db = SQLAlchemy(app)
db.init_app(app)


##Cafe TABLE Configuration
class Cafe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f'{self.name}'

    def to_dict(self):
        # Method 1.
        dictionary = {}
        # Loop through each column in the data record
        for column in self.__table__.columns:
            # Create a new dictionary entry;
            # where the key is the name of the column
            # and the value is the value of the column
            dictionary[column.name] = getattr(self, column.name)
        return dictionary


with app.app_context():
    db.create_all()


# Add Cafe Form configuration
class CafeForm(FlaskForm):
    name = StringField('Cafe name', validators=[DataRequired()])
    map_url = StringField('Cafe Location on Google Maps (URL)', validators=[DataRequired(), URL()])
    img_url = StringField('Cafe Image on Google Images (URL)', validators=[DataRequired(), URL()])
    location = StringField('Where is the cafe located?', validators=[DataRequired()])
    seats = StringField('How many seats? (Roughly)', validators=[DataRequired()])
    coffee_price = StringField("What is the average price of a black coffee (in £'s)?")
    has_toilet = BooleanField('Is there a toilet?')
    has_wifi = BooleanField('Is there wifi available?')
    has_sockets = BooleanField('Are there power sockets available?')
    can_take_calls = BooleanField('Is it possible to take phone calls?')
    submit = SubmitField('Submit')


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/cafes", methods=["GET", "POST"])
def cafes():
    all_cafes = requests.get("http://127.0.0.1:5000/all")
    data = all_cafes.json()
    all_cafes = data['cafes']
    place_name = request.args.get("search")
    if place_name:
        return redirect(url_for("search_results", location=place_name))
    return render_template("Cafes.html", all_cafes=all_cafes)


@app.route('/documentation')
def documentation():
    return render_template("documentation.html")


## HTTP GET - Read Record
@app.route("/random_cafe", methods=["GET"])
def get_random_cafe():
    all_cafes = db.session.query(Cafe).all()
    random_cafe = random.choice(all_cafes)
    return jsonify(cafe=random_cafe.to_dict())


@app.route("/random", methods=["GET"])
def random_cafe():
    response = requests.get("http://127.0.0.1:5000/random_cafe")
    cafe = response.json()
    place_name = request.args.get("search")
    if place_name:
        return redirect(url_for("search_results", location=place_name))
    return render_template("random.html", cafe=cafe["cafe"])

@app.route("/all", methods=["GET"])
def get_all_cafes():
    cafes = db.session.query(Cafe).all()
    return jsonify(cafes=[cafe.to_dict() for cafe in cafes])


@app.route("/search", methods=["GET"])
def search_for_cafe():
    query_cafe = request.args.get("loc")
    all_cafes = db.session.query(Cafe).filter_by(location=query_cafe)
    if all_cafes:
        return jsonify(cafes=[cafe.to_dict() for cafe in all_cafes])
    else:
        return render_template("no_cafe.html")


@app.route('/add', methods=["GET", "POST"])
def add_cafe():
    cafe_form = CafeForm()
    if cafe_form.validate_on_submit():
        new_cafe = Cafe(
            name=request.form.get("name"),
            map_url=request.form.get("map_url"),
            img_url=request.form.get("img_url"),
            location=request.form.get("location"),
            has_sockets=bool(request.form.get("has_sockets")),
            has_toilet=bool(request.form.get("has_toilet")),
            has_wifi=bool(request.form.get("has_wifi")),
            can_take_calls=bool(request.form.get("can_take_calls")),
            seats=request.form.get("seats"),
            coffee_price=request.form.get("coffee_price"))
        db.session.add(new_cafe)
        db.session.commit()
        return redirect(url_for('cafes'))
    return render_template('add.html', form=cafe_form)


@app.route("/search_results/<location>", methods = ["GET", "POST"])
def search_results(location):
    all_cafes = requests.get(f"http://127.0.0.1:5000/search?loc={location.title()}")
    data = all_cafes.json()
    all_cafes = data['cafes']
    place_name = request.args.get("search")
    if place_name:
        return redirect(url_for("search_results", location=place_name))
    if all_cafes:
        return render_template("Cafes.html", all_cafes=all_cafes)
    else:
        return render_template("no_cafe.html")


## HTTP PUT/PATCH - Update Record
@app.route("/update-price/<int:cafe_id>", methods=["GET", "PATCH"])
def patch_new_price(cafe_id):
    new_price = request.args.get("new_price")
    cafe = db.session.query(Cafe).get(cafe_id)
    if cafe:
        cafe.coffee_price = new_price
        db.session.commit()
        return jsonify(response={"success": "Successfully updated the price."}), 200
    else:
        return jsonify(error={"Not Found": "Sorry a cafe with that id was not found in the database"}), 404


# HTTP DELETE - Delete Record
@app.route("/report-closed/<int:cafe_id>", methods=["GET", "DELETE"])
def delete_cafe(cafe_id):
    api_key = request.args.get("api_key")
    cafe = db.session.query(Cafe).get(cafe_id)
    if api_key == "TopSecretAPIKey":
        if cafe:
            db.session.delete(cafe)
            db.session.commit()
            return jsonify(response={"success": "Successfully removed cafe from database."}), 200
        else:
            return jsonify(error={"Not Found": "Sorry a cafe with that id was not found in the database"}), 404
    else:
        return jsonify(response={"error": "Sorry, that's not allowed. Make sure you have the correct api_key."}), 403


if __name__ == '__main__':
    app.run(debug=True)
