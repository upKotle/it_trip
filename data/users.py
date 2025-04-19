import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(100), nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String(120), index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    history = sqlalchemy.Column(sqlalchemy.String(500), nullable=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    modified_date = sqlalchemy.Column(sqlalchemy.DateTime,
                                    default=datetime.datetime.now,
                                    onupdate=datetime.datetime.now)

    def set_password(self, password):
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        if not self.hashed_password or not password:
            return False
        return check_password_hash(self.hashed_password, password)

    def __repr__(self):
        return f'<User {self.id} {self.email}>'