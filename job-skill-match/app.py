import os
from pathlib import Path

from flask import Flask

import models

# app config
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASS")}@{os.getenv("DB_HOST")}/job-skill-match'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['HERE'] = Path(__file__).parent

models.init_app(app)

# routes
@app.route('/')
def hello():
    return {"hello": "world"}


if __name__ == '__main__':
    with app.app_context():
        results = models.Jobs.query.filter(models.Jobs.jobtitle.ilike('%AWS%')).all()
        # results = models.Jobs.query.filter(models.Jobs.__ts_vector__.match('AWS')).all()
        print(results)
