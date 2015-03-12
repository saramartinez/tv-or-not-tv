from flask import Flask, render_template, redirect, request, session, flash, jsonify
from model import session as modelsession
from model import User, Show, Service, Favorite, CachedService, CachedListing, CachedSearch
import os
import requests
import json
import hashlib
from time import time, mktime
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ['APP_SECRET_KEY']
ROVI_LISTINGS_API_KEY = os.environ['ROVI_TV_LISTINGS_API_KEY']
ROVI_SEARCH_API_KEY = os.environ['ROVI_METADATA_SEARCH_API_KEY']
ROVI_SEARCH_SECRET_KEY = os.environ['ROVI_METADATA_SHARED_SECRET']

UNIX_TIME = int(time())
SIG = hashlib.md5(ROVI_SEARCH_API_KEY + ROVI_SEARCH_SECRET_KEY + str(UNIX_TIME)).hexdigest()
NOW = datetime.utcnow()
CURRENT_TIMESTAMP = mktime(NOW.timetuple())
WEEK_IN_SECONDS = 604800

@app.route("/")
def index():
    """Shows the index."""
    return render_template("index.html")

@app.route("/signup", methods=['GET'])
def show_signup():
    """Display registration form"""
    return render_template("signup.html")

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

    existing_user = modelsession.query(User).filter(User.email == new_email).first()

    if existing_user == None:
        new_user = User(
            name=name,
            email=new_email,
            password=new_password,
            zipcode=zipcode,
            service_id=service_id,
            timezone=timezone)
        modelsession.add(new_user)
        modelsession.commit()
        session['logged_in'] = True
        session['id'] = new_user.id
        flash("Successfully created account. Add your favorite shows to get personalized listings!")
        return redirect("/")
    else:
        flash("Your email address is already associated with an account. Please log in.")
        return redirect("/login")

@app.route("/find-provider", methods=['GET'])
def find_provider():
    """
    AJAX request during user signup sends user zipcode
    from signup.html to query database for Cached Service
    results. If no cached data, query Rovi TV Listings
    API for possible service providers and add provider to
    database; then return to signup.html.
    """
    zipcode = str(request.args.get("zipcode"))

    ## look for zip param in table
    ## if request relatively fresh, return cached
    ## JSON object from table; otherwise hit API
    cached_service = modelsession.query(CachedService).filter(
        CachedService.zipcode_parameter == zipcode).first()

    if cached_service:
        cached_timestamp = mktime((cached_service.timestamp).timetuple())
    if cached_service and CURRENT_TIMESTAMP - cached_timestamp < WEEK_IN_SECONDS:
        services = json.loads(cached_service.results)
    else:
        listings_request = "http://api.rovicorp.com/TVlistings/v9/listings/services/postalcode/%s/info?locale=en-US&countrycode=US&format=json&apikey=%s" % (zipcode, ROVI_LISTINGS_API_KEY)

        listings_results = requests.get(listings_request)

        if listings_results.status_code == 200:
            providers = listings_results.json()

            services = providers['ServicesResult']['Services']['Service']

            if cached_service:
                cached_service.timestamp = NOW
                cached_service.results = json.dumps(services)
            else:
                store_results = CachedService(
                    zipcode_parameter=zipcode,
                    timestamp=NOW,
                    results=json.dumps(services))
                modelsession.add(store_results)
                modelsession.commit()
        else:
            services = None
            flash("There was an error retrieving service providers; please try again.")

    for each in services:
        existing_service = modelsession.query(Service).filter(Service.id == each['ServiceId']).first()
        if existing_service == None:
            new_service = Service(
                name=each['Name'],
                id=each['ServiceId'])
            modelsession.add(new_service)
            modelsession.commit()

    return jsonify({'services': services})

@app.route("/login", methods=['GET'])
def show_login():
    """Show login form only if user not logged in"""
    if "logged_in" not in session:
        return render_template("login.html")
    else:
        flash("You're already logged in!")
        return redirect('/')

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

    existing_user = modelsession.query(User).filter(User.email == new_email).first()

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
    session.pop('id', None)
    flash("You were logged out.")
    return redirect("/")

@app.route("/settings/")
def user_settings():
    """Displays user profile"""
    if session['id']:
        user_id = session['id']
    user_profile = modelsession.query(User).filter(User.id == user_id).one()
    return render_template("settings.html", id=user_id, user=user_profile)

@app.route("/settings/edit")
def edit_settings():
    """Displays template for user to edit profile"""
    if session['id']:
        user_id = session['id']
        user_profile = modelsession.query(User).filter(User.id == user_id).one()
    return render_template("edit-settings.html", id=user_id, user=user_profile)

@app.route("/settings/update", methods=["POST"])
def update_settings():
    """
    Updates user in database if they enter correct
    password when editing settings.
    """
    if session['id']:
        user_id = session['id']
        user_profile = modelsession.query(User).filter(User.id == user_id).one()

    old_password = request.form.get("old-password")
    new_email = request.form.get("email", None)
    new_password = request.form.get("new-password", None)
    new_name = request.form.get("username", None)
    new_zipcode = request.form.get("zipcode", None)
    new_service_id = request.form.get("service-provider", None)

    if old_password == user_profile.password:
        if new_email:
            user_profile.email = new_email
        if new_password:
            user_profile.password = new_password
        if new_name:
            user_profile.name = new_name
        if new_zipcode:
            user_profile.zipcode = new_zipcode
        if new_service_id:
            user_profile.service_id = new_service_id

        modelsession.commit()
        modelsession.refresh(user_profile)

        flash("Profile updated successfully.")

    else:
        flash("Incorrect password, please try again.")

    return redirect("/settings/")

@app.route("/search")
def search():
    """Shows search template if user goes directly to route"""
    return render_template("search.html")

@app.route("/search", methods=["POST"])
def search_results():
    """
    Based on user input, queries database to see if cached
    results exist for query string (within the last week).
    Otherwise, hits API for results and stores show info in
    shows table and JSON object from search results in
    cached_results table.
    """
    query = request.form.get('query')

    cached_search = modelsession.query(CachedSearch).filter(CachedSearch.query == query).first()

    if cached_search:
        cached_timestamp = mktime((cached_search.timestamp).timetuple())

    if cached_search and CURRENT_TIMESTAMP - cached_timestamp < WEEK_IN_SECONDS:
        json_results = json.loads(cached_search.results)
        results = json_results['searchResponse']['results']
    else:
        api_request = "http://api.rovicorp.com/search/v2.1/video/search?entitytype=tvseries&query=" + query + "&rep=1&include=synopsis%2Cimages&size=5&offset=0&language=en&country=US&format=json&apikey=" + ROVI_SEARCH_API_KEY + "&sig=" + SIG

        rovi_results = requests.get(api_request)

        if rovi_results.status_code == 200:
            json_results = rovi_results.json()

            if cached_search:
                cached_search.timestamp = NOW
                cached_search.results = json.dumps(json_results)
            else:
                ## save result to new table
                store_results = CachedSearch(
                    query=query,
                    timestamp=NOW,
                    results=(json.dumps(json_results)))
                modelsession.add(store_results)
                modelsession.commit()

            results = json_results['searchResponse']['results']
        else:
            results = None
            flash("There was an issue getting results. Please search again or reload the page.")

    if results:
        for each in results:
            result_title = each['video']['masterTitle']
            result_id = each['video']['ids']['cosmoId']

            if each['video']['synopsis']:
                result_synopsis = each['video']['synopsis']['synopsis']
            else:
                result_synopsis = None

            if each['video']['images']:
                result_img = each['video']['images'][0]['url']
            else:
                result_img = None

            existing_show = modelsession.query(Show).filter(Show.cosmoid == result_id).first()
            if existing_show == None:
                new_show = Show(
                    title=result_title,
                    cosmoid=result_id,
                    synopsis=result_synopsis,
                    img=result_img)
                modelsession.add(new_show)
                modelsession.commit()

    return render_template("search.html", results=results)

@app.route("/favorites", methods=['POST'])
def add_to_favorites():
    """
    Saves new database entry in favorites table with
    user's ID and show ID (foreign keys bridge users
    table and shows table).
    """
    shows = request.form.getlist("show")
    for show in shows:
        existing_favorite = modelsession.query(Favorite).filter(Favorite.show_id == show, Favorite.user_id == session['id']).first()
        if existing_favorite == None:
            new_favorite = Favorite(
                user_id=session['id'],
                show_id=show)
            modelsession.add(new_favorite)
            modelsession.commit()

    return redirect("/")

@app.route("/favorites/")
def show_favorites():
    """
    Queries favorites table with user's ID to determine
    which shows are saved as favorites, then passes
    to HTMl to display all.
    """
    if session['id']:
        user_id = session['id']
        favorites = modelsession.query(Favorite).filter(Favorite.user_id == user_id).all()
        favorite = favorites.sort()
    return render_template("favorites.html", id=user_id, favorites=favorites)

@app.route("/schedule/") ## paging int; 1 by default then increase
def show_listings(): ## bool / (id, is_cron)
    if session['id']:
        user_id = session['id']
        results = get_listings(user_id)
        results_list = results
        favorites = modelsession.query(Favorite).filter(Favorite.user_id == user_id).all()

    return render_template("schedule.html", schedule=results_list, favorites=favorites)

@app.route("/listings/")
def get_listings(user_id): ## bool / (id, is_cron) 
    """
    Gets user's first five favorites from database, then
    determine's user's service_id, current datetime and
    5 days from now to build API query. Results with
    broadcast times append to list to be returned to HTML.
    """
    if user_id:
        favorites = modelsession.query(Favorite).filter(Favorite.user_id == user_id).limit(5)
        serviceid = modelsession.query(User.service_id).filter(User.id == user_id).first()[0]

    start = NOW.strftime("%Y-%m-%dT%H%%3A%M%%3A%S.%fZ")

    results_list = []

    six_hours = 21600

    for favorite in favorites:
        cosmoid = favorite.show_id

        ## first check cached_listings table in database to
        ## see if there is a row matching the TV show's ID
        ## and service provider's ID
        cached_listings = modelsession.query(CachedListing).filter(CachedListing.show_id == cosmoid, CachedListing.service_id == serviceid).first()

        ## if there is a row in the table, see how fresh it is
        if cached_listings:
            cached_timestamp = mktime((cached_listings.timestamp).timetuple())

        ## if cached results exist AND they're recent, do this
        if cached_listings and CURRENT_TIMESTAMP - cached_timestamp < six_hours:
            json_results = json.loads(cached_listings.results)
            results = json_results['ProgramDetailsResult']['Schedule']['Airings']
        ## if nothing is cached or the cached
        ## results aren't recent, do this
        else:
            api_request = "http://api.rovicorp.com/TVlistings/v9/listings/programdetails/%s/%s/info?locale=en-US&copytextformat=PlainText&include=Program&imagecount=5&duration=10080&inprogress=true&startdate=%s&pagesize=6&format=json&apikey=%s" % (serviceid, cosmoid, start, ROVI_LISTINGS_API_KEY)

            rovi_results = requests.get(api_request)

            if rovi_results.status_code == 200:
                json_results = rovi_results.json()

                ## overwrites single row in db with updated timestamp and results
                if cached_listings:
                    cached_listings.timestamp = NOW
                    cached_listings.results = json.dumps(json_results)
                else:
                    ## save JSON object to CachedListing
                    store_results = CachedListing(
                        service_id=serviceid,
                        show_id=cosmoid,
                        timestamp=NOW,
                        results=(json.dumps(json_results)))
                    modelsession.add(store_results)
                    modelsession.commit()

                results = json_results['ProgramDetailsResult']['Schedule']['Airings']

                results = sorted(results, key=lambda results: results['AiringTime'])

                # for each in results:
                #     ## compare each to each to see if each['Copy'] and each['AiringTime'] are the same
                #     ## dict == key + copy; insert results list as value
                #     if each['AiringTime'] 

                #     each['Copy']

            else:
                flash("The request timed out. Please refresh the page.")
                results = None

        results_list.append(results)

        return results_list



if __name__ == "__main__":
    app.run(debug=True)
