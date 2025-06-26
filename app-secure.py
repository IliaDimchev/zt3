from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, TextAreaField, validators
import csv
import io
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Config for email
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'

mail = Mail(app)

# Config for database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///contacts.db'
db = SQLAlchemy(app)

# Contact model
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

# Contact form with validation
class ContactForm(Form):
    name = StringField('Име', [validators.InputRequired(), validators.Length(min=2, max=100)])
    email = StringField('Имейл', [validators.InputRequired(), validators.Email(), validators.Length(max=120)])
    message = TextAreaField('Съобщение', [validators.InputRequired(), validators.Length(min=10)])

# Simple auth decorator
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ContactForm(request.form)
    if request.method == 'POST' and form.validate():
        contact = Contact(name=form.name.data, email=form.email.data, phone=form.phone.data, message=form.message.data)
        db.session.add(contact)
        db.session.commit()

        # Send email
        msg = Message('Ново запитване от сайта', 
                      sender=app.config['MAIL_USERNAME'], 
                      recipients=['your-email@example.com'])
        msg.body = f"Име: {form.name.data}\nИмейл: {form.email.data}\nСъобщение:\nТелефоне: {form.phone.data}\n{form.message.data}"
        mail.send(msg)

        flash('Благодарим ти, ще се свържем с теб скоро!', 'success')
        return redirect(url_for('index'))
    return render_template('index.html', form=form)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash('Грешно потребителско име или парола', 'danger')
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_panel():
    contacts = Contact.query.order_by(Contact.id.desc()).all()
    return render_template('admin.html', contacts=contacts)

@app.route('/export')
@login_required
def export_contacts():
    contacts = Contact.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Message'])
    for c in contacts:
        writer.writerow([c.id, c.name, c.email, c.message])

    output.seek(0)
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=contacts.csv"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
