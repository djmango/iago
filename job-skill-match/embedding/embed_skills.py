import csv
import pathlib
import time

import pandas as pd
from sentence_transformers import SentenceTransformer

from ..app import db
from ..models import Skills

start = time.perf_counter()

HERE = pathlib.Path(__file__).parent

# load skills
with open(HERE/'jobs'/'skills.csv', 'r') as f:
    reader = csv.reader(f)
    skills = [x[0] for x in list(reader)]

# load model
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
print(f'Model load took {round(time.perf_counter() - start, 2)}s')

# embed
embeddings = model.encode(skills, show_progress_bar=True)
print(f'Embed took {round(time.perf_counter() - start, 2)}s')

# save locally
pd.DataFrame(list(zip(skills, embeddings)), columns=['Skill', 'Embedding']).to_csv(HERE/'skills_embedded.csv')
print('Written locally')

# insert records
values = [Skills(skill=skill, embedding=embedding.tolist()) for skill, embedding in zip(skills, embeddings)]
db.session.add_all(values)
db.session.commit()
print('Written to DB')
