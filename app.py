from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, URLMapping, User

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///url_shortener.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Function to generate a random short URL
def generate_short_url(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Create the database tables
with app.app_context():
    db.create_all()

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        new_user = User(username, hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

# Route for user logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout successful!', 'info')
    return redirect(url_for('login'))

# Route for the home page (authenticated)
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        long_url = request.form['long_url']
        # Generate a unique short URL
        short_url = generate_short_url()
        while URLMapping.query.filter_by(short_url=short_url).first() is not None:
            short_url = generate_short_url()

        # Store the mapping in the database
        new_mapping = URLMapping(short_url, long_url, current_user.id)
        db.session.add(new_mapping)
        db.session.commit()

        return redirect(url_for('result', short_url=short_url))
    return render_template('index.html')

# Route to display the result page with the shortened URL
@app.route('/result/<short_url>')
@login_required
def result(short_url):
    mapping = URLMapping.query.filter_by(short_url=short_url, user_id=current_user.id).first()
    if mapping:
        return render_template('result.html', short_url=short_url, long_url=mapping.long_url)
    flash('URL not found or unauthorized access.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    links = URLMapping.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html', links=links)

# Route to redirect to the original URL
@app.route('/<short_url>')
def redirect_url(short_url):
    mapping = URLMapping.query.filter_by(short_url=short_url).first()
    if mapping:
        return redirect(mapping.long_url)
    return "URL not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2050, debug=True)
