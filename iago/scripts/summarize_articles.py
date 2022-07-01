import time
start = time.perf_counter()
import header

import os
import tqdm
from datasets import Dataset
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from v0 import ai
from django.db.models import Q
from v0.models import Content
from v0.utils import chunks

print(f'{time.perf_counter()-start:.3f}s is cost of import')

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
start = time.perf_counter()

k = 5000
loops = 16

class ListDataset(Dataset):
    def __init__(self, original_list):
        self.original_list = original_list

    def __len__(self):
        return len(self.original_list)

    def __getitem__(self, i):
        return self.original_list[i]

for i in range(loops):
    articles = list(Content.objects.filter(summary={})[:k].values('pk', 'title', 'content', 'summary'))
    print(len(articles))

    texts = [x['content'] for x in articles]
    clean_texts = []
    for text in texts:
        # reduce to max tokens
        clean_text = text
        while len(ai.tokenizer(clean_text)['input_ids']) > ai.SUMMARIZER_CONFIG['MAX_TOKENS']:
            ten_percent = len(clean_text) // 10
            clean_text = clean_text[:-ten_percent]

        clean_texts.append(clean_text)

    summaries = []
    for s in tqdm.tqdm(ai.summarizer(clean_texts, min_length=ai.SUMMARIZER_CONFIG['MIN_LENGTH'], no_repeat_ngram_size=ai.SUMMARIZER_CONFIG['NO_REPEAT_NGRAM_SIZE'])):
        summaries.append(s['summary_text'])

    for i, article in enumerate(articles):
        current_summary = article['summary']
        current_summary[ai.SUMMARIZER_CONFIG['MODEL_NAME']] = summaries[i]
        Content.objects.filter(pk=article['pk']).update(summary=current_summary)


# chunk_size = 100
# # processes = 4

# def summarize(articles: list):
#     texts = [article.content for article in articles]
#     for article in articles:
#         if not ai.SUMMARIZER_CONFIG['MODEL_NAME'] in article.summary:
#             # reduce to max tokens
#             clean_text = article.content
#             while len(ai.tokenizer(clean_text)['input_ids']) > ai.SUMMARIZER_CONFIG['MAX_TOKENS']:
#                 ten_percent = len(clean_text) // 10
#                 clean_text = clean_text[:-ten_percent]

#             article.summary[ai.SUMMARIZER_CONFIG['MODEL_NAME']] = ai.summarizer(clean_text, min_length=ai.SUMMARIZER_CONFIG['MIN_LENGTH'], no_repeat_ngram_size=ai.SUMMARIZER_CONFIG['NO_REPEAT_NGRAM_SIZE'])[0]['summary_text']
#             article.save()

# # for article in tqdm.tqdm(articles):
# #     summarize(article)

# if __name__ == '__main__':
#     articles = list(Content.objects.all().order_by('updated_on')[:k])
#     print(k)
#     for chunk in tqdm.tqdm(chunks(articles, chunk_size), total=len(articles) // chunk_size):
#         summarize(chunk)
        
#     # with ThreadPool(processes) as p:
#     #     for i in tqdm.tqdm(p.imap(summarize, chunks(articles, chunk_size)), total=len(articles)//chunk_size):
#     #         pass

print(f'Took {time.perf_counter()-start:.3f}s')
