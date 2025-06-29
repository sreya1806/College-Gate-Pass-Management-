from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db = SQLAlchemy(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, faculty, security

# GatePass Model
class GatePass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    roll_no = db.Column(db.String(20), nullable=False)
    dob = db.Column(db.String(20), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    parent_name = db.Column(db.String(100), nullable=False)
    parent_number = db.Column(db.String(15), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='Pending')

    student = db.relationship('User', backref=db.backref('gate_passes', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home Route
@app.route('/')
def home():
    return render_template('home.html')

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])  
        role = request.form['role']

        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for('register'))

        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash("✅ Successfully Registered! Please Login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')

            if user.role == "student":
                return redirect(url_for('student_dashboard'))
            elif user.role == "faculty":
                return redirect(url_for('faculty_dashboard'))
            elif user.role == "security":
                return redirect(url_for('security_dashboard'))
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')

# Student Dashboard
@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != "student":
        return redirect(url_for('home'))

    requests = GatePass.query.filter_by(student_id=current_user.id).order_by(GatePass.request_date.desc()).all()
    return render_template('student_dashboard.html', requests=requests)

# Request Gate Pass
@app.route('/request_gatepass', methods=['GET', 'POST'])
@login_required
def request_gatepass():
    if request.method == 'POST':
        roll_no = request.form['roll_no']
        dob = request.form['dob']
        parent_name = request.form['parent_name']
        parent_number = request.form['parent_number']
        reason = request.form['reason']

        new_request = GatePass(student_id=current_user.id, roll_no=roll_no, dob=dob,
                               parent_name=parent_name, parent_number=parent_number, reason=reason)
        db.session.add(new_request)
        db.session.commit()
        flash("Wait for some time, request has been sent to faculty!", "info")
        return redirect(url_for('student_dashboard'))
    return render_template('request_gatepass.html')

# Faculty Dashboard
@app.route('/faculty_dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != "faculty":
        return redirect(url_for('home'))

    requests = GatePass.query.filter_by(status="Pending").all()
    return render_template('faculty_dashboard.html', requests=requests)

# Faculty Accept/Reject
@app.route('/update_request/<int:request_id>/<status>')
@login_required
def update_request(request_id, status):
    if current_user.role != "faculty":
        return redirect(url_for('home'))

    gatepass = GatePass.query.get(request_id)
    if gatepass:
        gatepass.status = status
        db.session.commit()
        flash(f"Gatepass request {status}!", "success")
    return redirect(url_for('faculty_dashboard'))

# Security Dashboard
@app.route('/security_dashboard')
@login_required
def security_dashboard():
    if current_user.role != "security":
        return redirect(url_for('home'))

    approved_requests = GatePass.query.filter(GatePass.status.in_(["Accepted", "Rejected"])).order_by(GatePass.request_date.desc()).all()
    return render_template('security_dashboard.html', requests=approved_requests)

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))


# Run the Flask App
if __name__== '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)