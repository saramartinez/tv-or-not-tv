from flask import Flask, render_template, redirect, request, session, flash, url_for
from model import session as modelsession
from model import User, Show, Service, Favorite

app = Flask(__name__)
app.secret_key = 'comingsoon'


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=['GET'])
def show_signup():
    """Display registration form"""
    return render_template("signup.html")

@app.route("/signup", methods=['POST'])
def process_signup():
    """Add user information to database"""
    new_email = request.form.get("email")
    new_password = request.form.get("password")

    existing_user = modelsession.query(User).filter(User.email==new_email).first()
    
    if existing_user == None:
        new_user = User(email=new_email, password=new_password)
        modelsession.add(new_user)
        modelsession.commit()
        session['user'] = new_user.id
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
    """Process user login"""
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
            session['user'] = True
            flash("Successfully logged in.")
            return redirect("/")

@app.route("/logout")
def logout():
    """Remove user from session"""
    session.pop('user', None)
    flash("You were logged out.")
    return redirect("/")

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/search", methods=["POST"])
def search_results():
    query = request.form.get('query')
    results = modelsession.query(Movie).filter(Movie.title.like("%" + query + "%")).limit(50).all()

    return render_template("movie_list.html", movies=results)

@app.route("/favorites/<int:id>")
def show_favorites(id):
    return render_template("favorites.html", id=id)


if __name__ == "__main__":
    app.run(debug = True)