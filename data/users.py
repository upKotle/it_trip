import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
import secrets


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(100), nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String(120), unique=True, nullable=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String(255), nullable=False)
    login_time = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    logout_time = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    price_history = sqlalchemy.Column(sqlalchemy.Text, nullable=True, default='')

    auth_tokens = orm.relationship("AuthToken", back_populates="user")
    remember_tokens = orm.relationship("RememberToken", back_populates="user")

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def add_price_to_history(self, price, waste_class, waste_volume, db_sess):
        """Добавляет цену в историю с классом отходов и объемом"""
        if self.price_history is None:
            self.price_history = ''

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.price_history = f"{timestamp}:{price:.2f}:{waste_class}:{waste_volume}\n{self.price_history}"

        # Ограничиваем историю 100 последними записями
        prices = [p for p in self.price_history.split('\n') if p.strip()][:100]
        self.price_history = '\n'.join(prices)

        db_sess.add(self)
        db_sess.commit()

    def get_price_history(self):
        """Возвращает историю цен с классом отходов и объемом"""
        if not self.price_history:
            return []

        history = []
        for entry in self.price_history.split('\n'):
            if entry.strip():
                try:
                    parts = entry.split(':')
                    timestamp = parts[0]
                    price = float(parts[1])
                    waste_class = parts[2] if len(parts) > 2 else None
                    volume = parts[3] if len(parts) > 3 else None

                    history.append({
                        'date': timestamp,
                        'price': price,
                        'waste_class': waste_class,
                        'volume': volume
                    })
                except (ValueError, IndexError):
                    continue
        return history

    def __repr__(self):
        return f'<User {self.id} {self.email}>'

class AuthToken(SqlAlchemyBase):
    __tablename__ = 'auth_tokens'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    token = sqlalchemy.Column(sqlalchemy.String(100), unique=True, nullable=False)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    expires_at = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)

    user = orm.relationship("User", back_populates="auth_tokens")


class RememberToken(SqlAlchemyBase):
    __tablename__ = 'remember_tokens'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    token = sqlalchemy.Column(sqlalchemy.String(100), unique=True, nullable=False)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    expires_at = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)

    user = orm.relationship("User", back_populates="remember_tokens")


class ErrorLog(SqlAlchemyBase):
    __tablename__ = 'error_logs'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    status_code = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    error_message = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    timestamp = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=True)

    user = orm.relationship("User")

