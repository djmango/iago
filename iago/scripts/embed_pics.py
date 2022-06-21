import header

import os
import time
import tqdm
from django.db import transaction
from v0.ai import embedding_model
from v0.models import UnsplashPhoto

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

TIMES_TO_REPEAT = 1
ITEMS_PER_LOOP = 10000

for i in range(TIMES_TO_REPEAT):
    print(UnsplashPhoto.objects.exclude(embedding_all_mpnet_base_v2__isnull=False).exclude(ai_description='').count())
    pics_to_embed = UnsplashPhoto.objects.exclude(embedding_all_mpnet_base_v2__isnull=False).exclude(ai_description='')[:ITEMS_PER_LOOP]
    pics_to_embed_pk = list(pics_to_embed.values_list('pk', flat=True))

    print(f'ouits touim to embed {pics_to_embed.count()} poics am i rouight lad')

    strings_to_embed = list(pics_to_embed.values_list('ai_description', flat=True))

    embeds = embedding_model.model.encode(strings_to_embed, show_progress_bar=True)
    embeds = embeds.tolist()

    k = 0
    start = time.perf_counter()
    with transaction.atomic():
        for i in tqdm.trange(len(pics_to_embed_pk)):
            UnsplashPhoto.objects.filter(pk=pics_to_embed_pk[i]).update(embedding_all_mpnet_base_v2=embeds[i])
            k+=1
    print(k)
    print(f'Took {time.perf_counter()-start:.3f}s')
