from flask import Flask, render_template, redirect, url_for, flash, request, make_response
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, logout_user, login_required, login_user, current_user
from data.users import User, AuthToken, RememberToken
from data import db_session
from templates.forms.user import RegisterForm, LoginForm
from templates.forms.calculator import WasteCalculatorForm
from waitress import serve
import os
import datetime
import secrets

app = Flask(__name__, template_folder="templates")
login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'My_SeCReT_KEY'),
    UPLOAD_FOLDER='static/img',
    DEBUG=os.getenv('DEBUG', 'True') == 'True',
    REMEMBER_COOKIE_DURATION=datetime.timedelta(days=30),
    SESSION_PROTECTION="strong"
)


def initialize_database():
    db_session.global_init("db/GreenAtom.db")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    try:
        return db_sess.query(User).get(user_id)
    finally:
        db_sess.close()


@app.route('/')
@app.route('/index')
def index():
    return render_template("main.html", user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            if form.password.data != form.password_again.data:
                flash('Пароли не совпадают', 'error')
                return render_template('register.html', form=form)

            if db_sess.query(User).filter(User.email == form.email.data).first():
                flash('Пользователь с таким email уже существует', 'error')
                return render_template('register.html', form=form)

            user = User(
                email=form.email.data,
                name=form.name.data,
                hashed_password=generate_password_hash(form.password.data)
            )

            db_sess.add(user)
            db_sess.commit()

            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        finally:
            db_sess.close()

    return render_template('register.html', form=form, user=current_user)


@login_manager.request_loader
def load_user_from_request(request):
    # Проверка обычного auth токена
    auth_token = request.cookies.get('auth_token')
    if auth_token:
        db_sess = db_session.create_session()
        try:
            token = db_sess.query(AuthToken).filter(
                AuthToken.token == auth_token,
                AuthToken.expires_at > datetime.datetime.now()
            ).first()
            if token:
                return token.user
        finally:
            db_sess.close()

    # Проверка remember me токена
    remember_token = request.cookies.get('remember_token')
    if remember_token:
        db_sess = db_session.create_session()
        try:
            token = db_sess.query(RememberToken).filter(
                RememberToken.token == remember_token,
                RememberToken.expires_at > datetime.datetime.now()
            ).first()
            if token:
                # Создаем новую сессию
                auth_token = AuthToken(
                    user_id=token.user_id,
                    token=secrets.token_urlsafe(64),
                    expires_at=datetime.datetime.now() + datetime.timedelta(days=1)
                )
                db_sess.add(auth_token)
                db_sess.commit()

                # Возвращаем пользователя и устанавливаем новый auth cookie
                response = make_response()
                response.set_cookie(
                    'auth_token',
                    value=auth_token.token,
                    expires=auth_token.expires_at,
                    httponly=True,
                    secure=not app.debug,
                    samesite='Lax'
                )
                return token.user
        finally:
            db_sess.close()

    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()

            if user and user.check_password(form.password.data):
                user.login_time = datetime.datetime.now()

                # Создаем обычный auth токен
                auth_token = AuthToken(
                    user_id=user.id,
                    token=secrets.token_urlsafe(64),
                    expires_at=datetime.datetime.now() + datetime.timedelta(days=1)
                )
                db_sess.add(auth_token)

                resp = make_response(redirect(url_for('index')))
                resp.set_cookie(
                    'auth_token',
                    value=auth_token.token,
                    expires=auth_token.expires_at,
                    httponly=True,
                    secure=not app.debug,
                    samesite='Lax'
                )

                # Если выбрано "Запомнить меня"
                if form.remember_me.data:
                    remember_token = RememberToken(
                        user_id=user.id,
                        token=secrets.token_urlsafe(64),
                        expires_at=datetime.datetime.now() + datetime.timedelta(days=30)
                    )
                    db_sess.add(remember_token)
                    resp.set_cookie(
                        'remember_token',
                        value=remember_token.token,
                        expires=remember_token.expires_at,
                        httponly=True,
                        secure=not app.debug,
                        samesite='Lax'
                    )

                db_sess.commit()
                login_user(user, remember=form.remember_me.data)
                return resp

            flash('Неверный email или пароль', 'error')
        except Exception as e:
            db_sess.rollback()
            flash('Ошибка при входе в систему', 'error')
            app.logger.exception("Login error")
        finally:
            db_sess.close()

    return render_template('login.html', form=form)


RATES = {
    '1': 222907.36,
    '2': 62468.26
}


@app.route('/waste-calculator', methods=['GET', 'POST'])
@login_required
def waste_calculator():
    form = WasteCalculatorForm()
    result = None
    waste_class = None
    waste_volume = None

    if request.method == 'POST' and form.validate_on_submit():
        waste_class = request.form.get('waste_class')
        waste_volume = float(request.form.get('waste_volume'))

        # Расчет стоимости
        rate = RATES.get(waste_class, 0)
        result = rate * waste_volume

        # Сохранение в историю пользователя
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).get(current_user.id)
            user.add_price_to_history(result, waste_class, waste_volume, db_sess)
            flash('Расчет выполнен успешно!', 'success')
        except Exception as e:
            db_sess.rollback()
            flash('Ошибка при сохранении расчета', 'error')
            app.logger.error(f"Error saving calculation: {str(e)}")
        finally:
            db_sess.close()

    # Получение истории расчетов пользователя
    price_history = []
    if current_user.is_authenticated:
        price_history = current_user.get_price_history()

    return render_template('waste_calculator.html',
                         form=form,
                         result=result,
                         waste_class=waste_class,
                         waste_volume=waste_volume,
                         price_history=price_history)


@app.route('/logout')
@login_required
def logout():
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).get(current_user.id)
        if user:
            user.logout_time = datetime.datetime.now()
            db_sess.add(user)

            # Удаляем auth токен
            auth_token = request.cookies.get('auth_token')
            if auth_token:
                token = db_sess.query(AuthToken).filter(
                    AuthToken.token == auth_token,
                    AuthToken.user_id == user.id
                ).first()
                if token:
                    db_sess.delete(token)

            # Удаляем remember токен
            remember_token = request.cookies.get('remember_token')
            if remember_token:
                token = db_sess.query(RememberToken).filter(
                    RememberToken.token == remember_token,
                    RememberToken.user_id == user.id
                ).first()
                if token:
                    db_sess.delete(token)

            db_sess.commit()

        logout_user()
        resp = make_response(redirect(url_for('index')))
        resp.delete_cookie('auth_token')
        resp.delete_cookie('remember_token')
        return resp
    except Exception as e:
        db_sess.rollback()
        flash('Ошибка при выходе из системы', 'error')
        app.logger.error(f"Logout error: {str(e)}")
        return redirect(url_for('index'))
    finally:
        db_sess.close()




def run_server():
    port = int(os.getenv("PORT", 5000))
    if app.config['DEBUG']:
        app.logger.setLevel(logging.DEBUG)
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        serve(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    initialize_database()
    run_server()