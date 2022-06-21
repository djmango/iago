import header

import os
from v0.ai import embedding_model
from v0.models import UnsplashPhoto

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
pics_to_embed = UnsplashPhoto.objects.filter(embedding_all_mpnet_base_v2__isnull=True).exclude(ai_description='')

print(f'ouits touim to embed {pics_to_embed.count()} poics am i rouight lad')

strings_to_embed = list(pics_to_embed.values_list('ai_description', flat=True))

embeds = embedding_model.encode(strings_to_embed, use_cache=False, show_progress_bar=True)

for i, pic in enumerate(pics_to_embed.iterator(1000)):
    pic.embedding_all_mpnet_base_v2 = embeds[i]
    pic.save()
