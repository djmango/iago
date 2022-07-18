import header

from v0.models import Content
from v0.utils import clean_str
from django.db.models import Q
import pandas as pd
from tqdm import tqdm
import re
from pathlib import Path

HERE = Path(__file__).parent


# to_migrate = Content.objects.filter(~Q(provider='medium') | (Q(provider='medium') & Q(popularity__medium__totalClapCount__gt=200))).values_list('uuid', 'thumbnail')
# to_migrate = Content.objects.filter(thumbnail_original__isnull=True).values_list('uuid', 'thumbnail')
# to_migrate = Content.objects.all()

# for content in tqdm(to_migrate.iterator(3000), total=to_migrate.count()):
#     skills_list = list(content.skills.values_list('name', flat=True))
#     if content.thumbnail:
#         if content.provider == 'medium':
#             content.thumbnail_original = content.thumbnail
#             if content.thumbnail_alternative:
#                 content.thumbnail = content.thumbnail_alternative.photo_image_url
#             content.tags = skills_list
#         elif content.provider == 'hbr':
#             content.thumbnail_original = content.thumbnail
#     else:
#         content.tags = skills_list

#     content.save()

# df = pd.read_excel(HERE/'data'/'hbr'/'hbr_fixed.xlsx')
# for i, row in tqdm(df.iterrows(), total=df.shape[0]):
#     # new = re.sub(r'(\s{0,1}\\\w)', '', repr(str(row['author']))[3:])
#     # new.replace(', ', ',')
#     # new.replace(',', ', ')
#     # Content.objects.filter(url=row['article-href']).update(author=new, title=row['article'])
#     if not pd.isnull(row['content']):
#         start_index = row['content'].find('Print') + 10 # lots of annoying spaces and stuff
#         fixed_content = row['content'][start_index:]
#         fixed_content = re.sub(r'^\s+',' ', fixed_content)
#         fixed_content = clean_str(fixed_content)
#         Content.objects.filter(url=row['article-href']).update(content=fixed_content)


# fix authors having a bunch of spaces and stuff
# to_clean = Content.objects.filter(provider='hbr').values_list('uuid', 'author')
# for uuid, author in tqdm(to_clean):
#     # so essentially we want to remove escaped strings and normalize spaces
#     # new = re.sub(r'(\s{0,1}\\\w)', '', author)

#     new = str(author)
#     new = new.replace(', and', ',and ')
#     new = new.replace(',', ', ')
#     new = new.replace("'", "")

# add plaintext skills as tags for the demo
to_tag = Content.objects.filter(tags=[])
for content in tqdm(to_tag.iterator(1000), total=to_tag.count()):
    content.tags = list(content.skills.values_list('name', flat=True))
    content.save()

    # Content.objects.filter(uuid=uuid).update(author=new)

# fix null embeds
# from v0.ai import embedding_model
# to_embed = Content.objects.filter(embedding_all_mpnet_base_v2__isnull=True).values_list('uuid', 'content')

# contents = [x[1] for x in to_embed]

# embeds = embedding_model.model.encode(contents, show_progress_bar=True)

# for i, uuid in tqdm(enumerate([x[0] for x in to_embed])):
#     Content.objects.filter(uuid=uuid).update(embedding_all_mpnet_base_v2=list(embeds[i]))

print('done!')