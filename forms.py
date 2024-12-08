from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, PasswordField, EmailField, IntegerField, DateField
from wtforms.validators import DataRequired, Email, Length

class RegisterForm(FlaskForm):
    fname = StringField('First Name', validators=[DataRequired(), Length(min=2, max=30)])
    lname = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=30)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = EmailField(label="Email", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password", validators=[DataRequired()])
    submit=SubmitField(label="Log In")

class TransferForm(FlaskForm):
    sender_card_num = StringField(label="Your Card", validators=[DataRequired()])
    cvv = StringField(label="CVV", validators=[DataRequired(), Length(3)])
    pin = StringField(label="PIN/PUC", validators=[DataRequired(), Length(max=4)])
    receiver_card_num = StringField(label="Receiver's Card", validators=[DataRequired()])
    transfer_sum = IntegerField(label="Transfer Sum", validators=[DataRequired()])
    submit=SubmitField(label="Transfer Sum") 

class AddCardForm(FlaskForm):
    card_num = StringField(label="Card Number", validators=[DataRequired()])
    cvv = IntegerField(label="CVV", validators=[DataRequired()])
    pin = IntegerField(label="PIN/PUC", validators=[DataRequired()])
    exp_date = StringField(label="Expiery Date", validators=[DataRequired()])
    submit=SubmitField(label="Add Card")

