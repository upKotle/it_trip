from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, EmailField, BooleanField
from wtforms.validators import DataRequired, ValidationError
from data import db_session
from data.users import User

class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')
    sumbitten = SubmitField('Вернуться на главную страницу')

class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

    def check_password(self):
        """Проверяет соответствие пароля пользователя в базе данных"""
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == self.email.data).first()
            if user and user.check_password(self.password.data):
                return True
            return False
        finally:
            db_sess.close()