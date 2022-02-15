import time
from pathlib import Path

import sqlalchemy
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import TSVECTOR

db = SQLAlchemy()
migrate = Migrate()

start = time.perf_counter()
HERE = Path(__file__).parent


def init_app(app):
    db.init_app(app)
    migrate.init_app(app, db, directory=app.config['HERE']/'migrations')

# custom database classes


class TSVector(sqlalchemy.types.TypeDecorator):
    impl = TSVECTOR

# models


class Jobs(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jobtitle = db.Column(db.String(255), nullable=False, unique=True)
    embedding = db.Column(db.ARRAY(db.Float), nullable=False)

    # __ts_vector__ = db.Column(TSVector(), db.Computed("to_tsvector('english', jobtitle)", persisted=True))
    # __table_args__ = (sqlalchemy.Index('ix_jobs___ts_vector__', __ts_vector__, postgresql_using='gin'),)

    def __repr__(self):
        return str(self.jobtitle)


class Skills(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    skill = db.Column(db.String(255), nullable=False, unique=True)
    embedding = db.Column(db.ARRAY(db.Float), nullable=False)

    def __repr__(self):
        return str(self.skill)
