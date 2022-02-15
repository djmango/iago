import csv
import pathlib
import time

import pandas as pd
from sentence_transformers import SentenceTransformer

from ..app import db
from ..models import Jobs

start = time.perf_counter()

HERE = pathlib.Path(__file__).parent

# load jobslist
with open(HERE/'jobs'/'jobtitles.csv', 'r') as f:
    reader = csv.reader(f)
    jobslist = [x[0] for x in list(reader)]

# load model
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
print(f'Model load took {round(time.perf_counter() - start, 2)}s')

# embed
embeddings = model.encode(jobslist, show_progress_bar=True)
print(f'Embed took {round(time.perf_counter() - start, 2)}s')

# save locally
pd.DataFrame(list(zip(jobslist, embeddings)), columns=['Jobtitle', 'Embedding']).to_csv(HERE/'jobstitles_embedded.csv')
print('Written locally')

# insert records
values = [Jobs(jobtitle=jobtitle, embedding=embedding.tolist()) for jobtitle, embedding in zip(jobslist, embeddings)]
db.session.add_all(values)
db.session.commit()
print('Written to DB')
