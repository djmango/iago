import header

import time
import os
import re
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from v0 import ai
from v0.models import MindtoolsSkillGroup, MindtoolsSkillSubgroup

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
start = time.perf_counter()

HERE = Path(__file__).parent

df = pd.read_csv(HERE/'data'/'mindtools'/'mindtools_advanced.csv')
print(df.shape)

def only_alphas(s):
    return str(re.findall(r'[a-z A-Z]+', s)[0]).strip()

print('Cleaning up data...')
df['skill_group'] = df['skill_group'].map(only_alphas)
print(df.head())

print('Generating group objects...')
embeds_group = ai.embedding_model.model.encode(df['skill_group'].unique(), show_progress_bar=True)
groups = []
for i, name in enumerate(df['skill_group'].unique()):
    group = MindtoolsSkillGroup().create(name, list(embeds_group[i]))
    groups.append(group)

MindtoolsSkillGroup.objects.bulk_create(groups)

print('Generating subgroup objects...')
embeds_subgroups = ai.embedding_model.model.encode(df['skill_subgroup'].values, show_progress_bar=True)
for i, row in tqdm(df.iterrows(), total=df.shape[0]):
    subgroup = MindtoolsSkillSubgroup().create(row['skill_subgroup'], embeds_subgroups[i])
    subgroup.group = MindtoolsSkillGroup.objects.get(name=row['skill_group'])
    subgroup.save()

print(f'Took {time.perf_counter()-start:.3f}s')
print('done!')