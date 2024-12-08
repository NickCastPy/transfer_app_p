from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from flask import abort
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from sqlalchemy import Integer, String
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
from dotenv import load_dotenv
from functions import identify_card_type, check_credentials
from forms import RegisterForm, LoginForm, AddCardForm, TransferForm
from psycopg2 import *
import os

# APP | DB
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
db = SQLAlchemy(app)

# BOOTSTRAP INIT

# Bootstrap5(app)

# LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(client_id):
    return db.get_or_404(Client, client_id)

def card_owner_required(f):
    @wraps(f)
    def decorated_function(card_num, *args, **kwargs):
        # Get the card from the database
        card = db.session.execute(db.select(Card).where(Card.card_num == card_num)).scalar()

        # Check if the card exists and belongs to the logged-in user
        if not card or card.owner_id != current_user.id:
            abort(403)  # Forbidden access
        
        return f(card_num, *args, **kwargs)
    return decorated_function

# Classes 

class Client(db.Model, UserMixin):
    __tablename__="clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # User details
    fname: Mapped[str] = mapped_column(String(250), nullable=False, unique=False)
    lname: Mapped[str] = mapped_column(String(250), nullable=False, unique=False)
    email: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False, unique=False)
    # PARENT | ONE
    cards = relationship("Card", back_populates="owner", cascade="all, delete-orphan")

class Card(db.Model):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Card details
    card_num: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    cvv: Mapped[int] = mapped_column(Integer, nullable=True)
    pin: Mapped[int] = mapped_column(Integer, nullable=True)
    exp_date: Mapped[str] = mapped_column(String(5), nullable=False)
    card_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=True)
    # Link card to the client
    owner_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("clients.id"), nullable=False)
    # CHILD | MANY
    owner = relationship("Client", back_populates="cards")
    # PARENT | ONE
    transactions = relationship("Transaction", back_populates="card", cascade="all, delete-orphan")


class Transaction(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
     # Link transaction to the card
    card_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("cards.id"), nullable=False)
    # Transaction details
    receiver_card_num: Mapped[str] = mapped_column(String(16), nullable=False, unique=False)
    transfer_sum: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(250), nullable=False, unique=False)
    # CHILD | MANY
    card = relationship("Card", back_populates="transactions")


# with app.app_context():
#     db.create_all()

# ROUTES
    # HOME
@app.route("/")
def home():
    try:
        user_cards = db.session.execute(db.select(Card).where(Card.owner_id == current_user.id)).scalars().all()
        card_transactions = {}
        for card in user_cards:
            # Transactions sent by the current card
            sent_transactions = card.transactions

            # Transactions received by the current card
            received_transactions = db.session.execute(
                db.select(Transaction).where(Transaction.receiver_card_num == card.card_num)
            ).scalars().all()

            # Combine sent and received transactions for this card
            card_transactions[card.card_num] = {
                "sent": sent_transactions,
                "received": received_transactions,
            }
    except AttributeError:
        return redirect("/login")
    return render_template("personal_cabinet.html", current_user=current_user, cards=user_cards, transactions=card_transactions)

    # REGISTER

@app.route("/register", methods=["POST", "GET"])
def register():
    register_form = RegisterForm()
    if request.method=="POST" and register_form.validate_on_submit():
        new_user = Client(
            fname=request.form["fname"],
            lname=request.form["lname"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"], method="pbkdf2:sha256", salt_length=8),
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect('/')
    return render_template('register.html', form=register_form)

    # LOG IN

@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if request.method=="POST":
        email = request.form["email"]
        password = request.form["password"]
        selected_client = db.session.execute(db.select(Client).where(Client.email==email)).scalar()

        if check_password_hash(selected_client.password, password):
            login_user(selected_client)
            return redirect(url_for('home'))
    return render_template("login.html", form=login_form)

    # TRANSFER


@app.route("/transfer_money/<card_num>")
@login_required
@card_owner_required
def transfer_money(card_num):
    selected_card = db.session.execute(db.select(Card).where(Card.card_num==card_num)).scalar()
    transfer_form = TransferForm(
        sender_card_num=card_num,
        cvv=selected_card.cvv,
        pin=selected_card.pin
    )
    return render_template("transfer.html", card=selected_card, form=transfer_form)

@app.route("/process_transfer", methods=["POST", "PATCH"])
@login_required
def process_transfer():
    selected_card = db.session.execute(db.select(Card).where(Card.card_num==request.form["sender_card_num"])).scalar()
    receiver_card = db.session.execute(db.select(Card).where(Card.card_num==request.form["receiver_card_num"])).scalar()
    transfer_sum = int(request.form["transfer_sum"])

    if selected_card.amount >= transfer_sum:
        # TRANSFER THE SUM
        print("Credentials valid. Proceeding with transfer...")
        selected_card.amount -= transfer_sum
        receiver_card.amount += transfer_sum
        print("Updated amounts:", selected_card.amount, receiver_card.amount)
        # TRANSACTION LOGGING
        transaction = Transaction(
            card_id=selected_card.id,
            receiver_card_num=request.form["receiver_card_num"],
            transfer_sum=request.form["transfer_sum"],
            status="COMPLETE"
        )
        db.session.add(transaction)
        db.session.commit()
        return redirect('/add_card')
    return redirect("/")

@login_required
@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")

@login_required
@app.route("/add_card", methods=["POST", "GET"])
def add_card():
    card_form = AddCardForm()
    if request.method=="POST" and card_form.validate_on_submit():
        try:
            new_card = Card(
                card_num=request.form["card_num"],
                cvv=request.form["cvv"],
                pin=request.form["pin"],
                exp_date=request.form["exp_date"],
                card_type=identify_card_type(request.form["card_num"]),
                amount=32000,
                owner=current_user
            )
            db.session.add(new_card)
            db.session.commit()
            return redirect(url_for('home'))
        except ValueError:
            return "Invalid expiration date format. Use MM/YY."
        
    return render_template("add_card.html", form=card_form, user=current_user)

if __name__ == "__main__":
    app.run(debug=True, port=5004)