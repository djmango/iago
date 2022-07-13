import header

import time
import os
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from v0 import ai, index
from v0.models import Content
from v0.utils import truncateTextNTokens, mediumReadtime

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
start = time.perf_counter()

HERE = Path(__file__).parent

df = pd.read_excel(HERE/'data'/'hbr'/'hbr_fixed.xlsx')
print(df.shape)

rows_to_delete = []

# clean up data
print('Cleaning up data...')
for i, row in tqdm(df.iterrows(), total=df.shape[0]):
    if not pd.isnull(row['content']):
        start_index = row['content'].find('Print') + 40 # lots of annoying spaces and stuff
        df.loc[i, 'content'] = row['content'][start_index:]
    else:
        rows_to_delete.append(i)

df.drop(rows_to_delete, inplace=True)
print(df.shape)

# embed content
print('Embedding content...')
embeds = ai.embedding_model.model.encode(df['content'].values, show_progress_bar=True)

# truncate texts for summarization
# print('Truncating text to max_tokens...')
# clean_texts = [truncateTextNTokens(x)[0] for x in tqdm(df['content'])]

# summarize
# summaries = []
# print('Generating summaries...')
# for s in tqdm(ai.summarizer(clean_texts, min_length=ai.SUMMARIZER_CONFIG['MIN_LENGTH'], no_repeat_ngram_size=ai.SUMMARIZER_CONFIG['NO_REPEAT_NGRAM_SIZE'])):
#     summaries.append(s['summary_text'])

contents = []
print('Generating content objects...')
for i, row in tqdm(df.iterrows(), total=df.shape[0]):
    content = Content()

    content.title = row['article']
    content.author = repr(str(row['author']))[3:]
    content.url = row['article-href']
    content.provider = Content.providers.hbr
    content.type = Content.types.article
    content.content = row['content']
    if not pd.isnull(row['thumbnail-src']):
        content.thumbnail = 'https://hbr.org' + row['thumbnail-src']

    # populate the rest of the fields
    content.content_read_seconds = mediumReadtime(content.content)  # NOTE might be messed up because of all the newlines
    # lol i know that the express api sorts by popularity on medium articles so this is my hack to get to the front of the line
    content.popularity['medium'] = {'totalClapCount': 9999999999}

    # ai stuff
    # embed
    if len(embeds) > i:
        content.embedding_all_mpnet_base_v2 = list(embeds[i])

        # summarize
        # content.summary = summaries[i]

        # thumbnail
        img = index.unsplash_photo_index.query(content.embedding_all_mpnet_base_v2, k=1, use_cached=False)[0][0]
        content.thumbnail_alternative = img

    contents.append(content)

Content.objects.bulk_create(contents)

# okay now we have it saved we do relationships
for content in tqdm(contents):
    if content.embedding_all_mpnet_base_v2 is not None:
        skills, rankings, query_vector = index.skills_index.query(content.embedding_all_mpnet_base_v2, k=5, min_distance=.21)
        content.skills.set(skills)

print(f'Took {time.perf_counter()-start:.3f}s')
