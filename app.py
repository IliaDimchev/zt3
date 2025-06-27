from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from email.header import Header
from email.utils import formataddr
import time
import os
import csv
import io


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")

# Настройки за база данни
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///requests.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Настройки за имейл
app.config['MAIL_SERVER'] = 'trot.bg'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.environ.get("SENDER_EMAIL")
app.config['MAIL_PASSWORD'] = os.environ.get('SENDER_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("SENDER_EMAIL")

mail = Mail(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Модел за запитване
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=False)

# Потребител за админ
class Admin(UserMixin):
    id = 1
    username = os.environ.get("ADMIN_LOGIN")
    password = os.environ.get("ADMIN_PASSWORD")

@login_manager.user_loader
def load_user(user_id):
    if user_id == "1":
        return Admin()
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form['username'] == Admin.username and request.form['password'] == Admin.password:
            login_user(Admin())
            return redirect(url_for('admin_panel'))
        flash("Грешни данни за вход", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form.get("website"):  # honeypot
            print("SPAM: Honeypot triggered")
            return redirect(url_for("index"))        
        
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")

        new_request = ServiceRequest(name=name, email=email, phone=phone, message=message)
        db.session.add(new_request)
        db.session.commit()

        try:
            # Красив "From" адрес
            sender_name = str(Header("TROT.BG", 'utf-8'))
            sender_email = os.environ.get("SENDER_EMAIL")
            formatted_sender = formataddr((sender_name, sender_email))

            admin_msg = Message(
            subject=str(Header(f"Запитване от {name} - Segway ZT3 Pro", 'utf-8')),
            recipients=["dimchev.ilia@gmail.com"],
            body=f"Name: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}",
            sender=formatted_sender,
            charset='utf-8')

            mail.send(admin_msg)

            confirmation = Message(
            subject=str(Header("Потвърждение за получено запитване!", 'utf-8')),
            recipients=[email],
            sender=formatted_sender,
            charset='utf-8')
            
            confirmation.body = (
            f"Здравейте, {name}!\n\n"
            "Благодарим, че се свързахте с нас. Ще се свържем с вас относно отключването на скоростта на Segway ZT3 Pro до 40 км/ч съвсем скоро!.\n\n"
            "Поздрави,\nTROT.BG")

            confirmation.html = render_template("email_confirmation.html", name=name)

            mail.send(confirmation)
        except Exception as e:
            flash("Exception:", e)

        flash('Благодарим Ви! Ще се свържем с Вас съвсем скоро!', 'success')
        return redirect(url_for('index'))
    return render_template('index.html')

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if request.form.get("website"):  # honeypot
            print("SPAM: Honeypot triggered")
            return redirect(url_for("thank_you"))

        try:
            start_time = float(request.form.get("form_start", 0))
            if time.time() - start_time < 2:
                print("SPAM: Too fast")
                return redirect(url_for("thank_you"))
        except ValueError:
            return redirect(url_for("thank_you"))

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")

        new_request = ServiceRequest(name=name, email=email, phone=phone, message=message)
        db.session.add(new_request)
        db.session.commit()

        try:
            # Красив "From" адрес
            sender_name = str(Header("TROT.BG", 'utf-8'))
            sender_email = os.environ.get("SENDER_EMAIL")
            formatted_sender = formataddr((sender_name, sender_email))

            admin_msg = Message(
            subject=str(Header(f"Request from {name} - TROT", 'utf-8')),
            recipients=["dimchev.ilia@gmail.com"],
            body=f"Name: {name}\nEmail: {email}\nPhone: {phone}\nMessage: {message}",
            sender=formatted_sender,
            charset='utf-8')

            mail.send(admin_msg)

            confirmation = Message(
            subject=str(Header("TROT.BG - Request Received", 'utf-8')),
            recipients=[email],
            sender=formatted_sender,
            charset='utf-8')
            
            confirmation.body = (
            f"Здравейте, {name}!\n\n"
            "Благодарим, че се свързахте с нас. Ще се свържем с вас възможно най-скоро.\n\n"
            "Поздрави,\nTROT.BG")

            confirmation.html = render_template("email_confirmation.html", name=name)

            mail.send(confirmation)
        except Exception as e:
            print("Exception:", e)
        
        return redirect(url_for("thank_you"))
    return render_template("index.html", timestamp=time.time())

@app.route("/admin")
@login_required
def admin_panel():
    contacts = ServiceRequest.query.order_by(ServiceRequest.id.desc()).all()
    return render_template("admin.html", contacts=contacts)

@app.route("/admin/delete/<int:request_id>", methods=["POST"])
@login_required
def delete_request(request_id):
    req = ServiceRequest.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    flash("Запитването е изтрито.")
    return redirect(url_for("admin_panel"))

@app.route("/admin/export")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Име", "Имейл",  "Телефон", "Съобщение"])

    for req in ServiceRequest.query.all():
        writer.writerow([req.id, req.name, req.email, req.phone, req.message])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype='text/csv',
                     download_name='trot_requests.csv',
                     as_attachment=True)

# Само за локална разработка
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

