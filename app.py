from flask import Flask, render_template, redirect, request, session, flash, url_for, jsonify
from model import session as modelsession
from model import User, Show, Service, Favorite
from string import ascii_lowercase
import sys
import os
import requests
import json
import hashlib
from time import time

app = Flask(__name__)
app.secret_key = 'comingsoon'
ROVI_LISTINGS_API_KEY = os.environ['ROVI_TV_LISTINGS_API_KEY']
ROVI_SEARCH_API_KEY = os.environ['ROVI_METADATA_SEARCH_API_KEY']
ROVI_SEARCH_SECRET_KEY = os.environ['ROVI_METADATA_SHARED_SECRET'] 

@app.route("/")
def index():
    """Shows the index."""
    return render_template("index.html")

@app.route("/signup", methods=['GET'])
def show_signup():
    """Display registration form"""
    return render_template("signup.html")

@app.route("/find-provider", methods=['GET'])
def find_provider():
    """
    AJAX request sends user zipcode from signup.html to
    query Rovi TV Listings API for possible service 
    providers during user signup and add provider to
    database if not already there; then and return to
    signup.html.
    """
    zipcode = request.args.get("zipcode")
    providers = requests.get("http://api.rovicorp.com/TVlistings/v9/listings/services/postalcode/" + str(zipcode) + "/info?locale=en-US&countrycode=US&format=json&apikey=" + ROVI_LISTINGS_API_KEY).json()
    services = providers['ServicesResult']['Services']['Service']
    for each in services:
        existing_service = modelsession.query(Service).filter(Service.id == each['ServiceId']).first()
        if existing_service == None:
            new_service = Service(name=each['Name'], id=each['ServiceId'])
            modelsession.add(new_service)
            modelsession.commit()
    return jsonify({'services': services})


@app.route("/signup", methods=['GET', 'POST'])
def process_signup():
    """
    Get user information from signup.html on form submit
    and add as new user in database, then redirect to
    index. If user already exists, redirect to login
    page. Adds session cookies for logged_in = True and
    id = user.id.
    """
    new_email = request.form.get("email")
    new_password = request.form.get("password")

    name = request.form.get("username")
    zipcode = request.form.get("zipcode")
    service_id = request.form.get("service-provider")
    timezone = request.form.get("timezone")

    existing_user = modelsession.query(User).filter(User.email==new_email).first()
    
    if existing_user == None:
        new_user = User(name=name, email=new_email, password=new_password, zipcode=zipcode, service_id=service_id, timezone=timezone)
        modelsession.add(new_user)
        modelsession.commit()
        session['logged_in'] = True
        session['id'] = new_user.id
        flash("Successfully created account. Add your favorite shows to get personalized listings!")
        return redirect("/")
    else:
        flash("Your email address is already associated with an account. Please log in.")
        return redirect("/login")

@app.route("/login", methods=['GET'])
def show_login():
    """Show login form only if user not logged in"""
    if "user" not in session:
        return render_template("login.html")
    else:
        flash("You're already logged in!")
        return redirect('/') 

# Allow existing users to log in
@app.route("/login", methods=['POST'])
def process_login():
    """
    Checks to see if user exists in database and either
    logs them in or redirects to signup page.
    Adds session cookies for logged_in = True and
    id = user.id.
    """
    new_email = request.form.get('email')
    new_password = request.form.get('password')

    existing_user = modelsession.query(User).filter(User.email==new_email).first()

    if existing_user == None:
        flash("No user with that email exists. Please sign up!")
        return render_template("signup.html")
    else:
        if new_password != existing_user.password:
            flash("Incorrect password. Please try again.")
            return render_template("login.html")
        else:
            session['logged_in'] = True
            session['id'] = existing_user.id
            flash("Successfully logged in.")
            return redirect("/")

@app.route("/logout")
def logout():
    """Remove user.id and logged_in from session"""
    session.pop('logged_in', None)
    # session.pop('id', None)
    flash("You were logged out.")
    return redirect("/")

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/search", methods=["POST"])
def search_results():
    query = request.form.get('query')
    # db_results = modelsession.query(Show).filter(Show.title.like("%" + query + "%")).limit(50).all()
    unix_time = int(time())

    sig = hashlib.md5(ROVI_SEARCH_API_KEY + ROVI_SEARCH_SECRET_KEY + str(unix_time)).hexdigest()
    print sig

    api_request = "http://api.rovicorp.com/search/v2.1/video/search?entitytype=tvseries&query=" + query + "&rep=1&size=20&offset=0&language=en&country=US&format=json&apikey=" + ROVI_SEARCH_API_KEY + "&sig=" + sig

    rovi_results = requests.get(api_request).json()
    print rovi_results['searchResponse']['results'][0]
    
    return redirect("/")
    # return render_template("tv_list.html", db_shows=db_results, rovi_shows=rovi_results)

@app.route("/favorites/<int:id>")
def show_favorites(id):
    return render_template("favorites.html", id=id)

@app.route("/settings/<int:id>")
def user_settings(id):
    user_profile = modelsession.query(User).filter(User.id == id).one()
    return render_template("settings.html", id=id, user=user_profile)


if __name__ == "__main__":
    app.run(debug = True)