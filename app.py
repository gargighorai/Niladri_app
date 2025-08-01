from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from xhtml2pdf import pisa
from io import BytesIO
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Railway PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///local.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class Doctor(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    patients = db.relationship('Patient', backref='doctor', lazy=True)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Doctor.query.get(int(user_id))

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        doctor = Doctor.query.filter_by(username=request.form['username']).first()
        if doctor and doctor.password == request.form['password']:
            login_user(doctor)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', doctor=current_user)

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        patient = Patient(
            name=request.form['name'],
            age=request.form['age'],
            gender=request.form['gender'],
            symptoms=request.form['symptoms'],
            diagnosis=request.form['diagnosis'],
            doctor_id=current_user.id
        )
        db.session.add(patient)
        db.session.commit()
        return redirect('/dashboard')
    return render_template('add_patient.html')

@app.route('/patient_pdf/<int:patient_id>')
@login_required
def patient_pdf(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != current_user.id:
        return "Unauthorized", 403

    html = render_template('patient_pdf.html', patient=patient)
    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)

    if pisa_status.err:
        return "PDF generation error", 500

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=patient_{patient.id}.pdf'
    return response

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
