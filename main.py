from flask import Flask, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from flask_login import LoginManager
from data.users import User
from data import db_session
from templates.forms.user import RegisterForm, LoginForm
from waitress import serve
from os import getenv

# Инициализация приложения
app = Flask(__name__, template_folder="templates")
login_manager = LoginManager(app)

# Конфигурация приложения
app.config.update(
    SECRET_KEY=getenv('SECRET_KEY', 'My_SeCReT_KEY'),
    UPLOAD_FOLDER='/static/img',
    DEBUG=getenv('DEBUG', True)
)


def initialize_database():
    """Инициализация базы данных"""
    db_session.global_init("db/GreenAtom.db")


@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя для Flask-Login"""
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/')
def index():
    """Главная страница"""
    return render_template("main.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    form = RegisterForm()

    if form.validate_on_submit():
        # Если нажата кнопка "Вернуться на главную"
        if form.sumbitten.data:
            return redirect(url_for('index'))

        # Проверка совпадения паролей
        if form.password.data != form.password_again.data:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html', form=form)

        db_sess = db_session.create_session()

        # Проверка существования пользователя
        if db_sess.query(User).filter(User.email == form.email.data).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('register.html', form=form)

        # Создание нового пользователя
        user = User(
            email=form.email.data,
            name=form.name.data,
            hashed_password=generate_password_hash(form.password.data)
        )

        db_sess.add(user)
        db_sess.commit()

        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Авторизация пользователя"""
    form = LoginForm()

    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()

        if user and user.check_password(form.password.data):
            # Здесь должна быть логика входа пользователя
            return redirect("/")

        flash("Неправильный логин или пароль", "error")
        return render_template('login.html', form=form)

    return render_template('login.html', title='Авторизация', form=form)


def run_server():
    """Запуск сервера"""
    port = int(getenv("PORT", 5000))
    if app.config['DEBUG']:
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        serve(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    initialize_database()
    run_server()