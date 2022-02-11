import time

start = time.perf_counter()
import csv
import os
import pathlib

import sqlalchemy as db
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.declarative import declarative_base

print(f'Load took {round(time.perf_counter() - start, 2)}s')


HERE = pathlib.Path(__file__).parent

# database connection
engine = db.create_engine(f'postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASS")}@{os.getenv("DB_HOST")}/iago', echo=True)
connection = engine.connect()
Base = declarative_base(connection)

# tables

class Jobs(Base):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jobtitle = db.Column(db.String(255), nullable=False, unique=True)
    embedding = db.Column(db.ARRAY(db.Float), nullable=False)

    def __repr__(self):
        return str(self.jobtitle)
Jobs.__table__.create(bind=engine, checkfirst=True)

print(f'DB conn took {round(time.perf_counter() - start, 2)}s')

# load jobslist
with open(HERE/'jobtitles.csv', 'r') as f:
    reader = csv.reader(f)
    jobslist = [x[0] for x in list(reader)]

# load model
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
print(f'Model load took {round(time.perf_counter() - start, 2)}s')

# embed
embeddings = model.encode(jobslist, show_progress_bar=True)
print(f'Embed took {round(time.perf_counter() - start, 2)}s')

# insert records
with db.orm.Session(bind=connection) as session:

    # values = [{'jobtitle': jobtitle, 'embedding': embedding.tolist()} for jobtitle, embedding in zip(jobslist, embeddings)]
    values = [Jobs(jobtitle=jobtitle, embedding=embedding.tolist()) for jobtitle, embedding in zip(jobslist, embeddings)]
    # connection.execute(Jobs.__table__.insert(), values)
    session.add_all(values)
    session.commit()

    print('done')
