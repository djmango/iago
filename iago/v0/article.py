import json
import logging
import re
import time

import requests
from iago.settings import LOGGING_LEVEL_MODULE

from v0 import ai, index
from v0.models import Content
from v0.utils import clean_str

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)


def medium_to_markdown(text_block: dict, i: int, paragraphs_raw: list[dict]) -> str:
    # medium types

    # text blocks
    # 1 is normal text
    # 3 is header
    # 4 is image
    # 6 is quote
    # 7 is also quote block
    # 8 is code block
    # 9 is bullet list
    # 10 is numbered list
    # 11 is iframe, not easy to handle
    # 13 is a subtitle
    # 14 is an embedded link

    # markup
    # 1 is bold
    # 3 is link
    # 10 is inline code

    # first we do inline markup
    # so to since making something markup changes its char count, we have to keep track of the original string and the new string and keep an index of where the last change ended in the original string
    original_text = text_block['text']
    markdown_text = ""
    last_index = 0
    if 'markups' in text_block and len(text_block['markups']) > 0:
        for markup in text_block['markups']:
            modified_subtext = original_text[markup['start']-last_index:markup['end']-last_index]  # we only want to edit the part that has the rule applied to it
            if markup['type'] == 1:
                modified_subtext = "**" + modified_subtext + "**"
            elif markup['type'] == 2:
                modified_subtext = "*" + modified_subtext + "*"
            elif markup['type'] == 3 and 'href' in markup:  # sometimes its linking to an internal reference like a user or something so we dont need to link that right now
                modified_subtext = "[" + modified_subtext + "]" + "(" + markup['href'] + ")"

            markdown_text += original_text[:markup['start']-last_index] + modified_subtext
            original_text = original_text[markup['end']-last_index:]
            last_index = markup['end']

        # add the rest of the text that hasn't been modified
    markdown_text += original_text

    # then we clean up the text
    # NOTE we cant do this it will break our new inline markup - gotta figure out a way to differentiate between markup we add and the accidental stuff thats there because of unclean text
    # https://tech.saigonist.com/b/code/escaping-special-characters-markdown.html
    # text = text.replace('_', '\_').replace('*', '\*').replace('`', '\`')
    text = markdown_text

    if i > 0:
        last_type = paragraphs_raw[i-1]['type']
    else:
        last_type = None
    # then we format the whole block according to the type
    if text_block['type'] == 1:  # normal text
        pass
    elif text_block['type'] == 3:  # header
        if last_type == None:  # title
            text = f"# {text}"
        else:
            text = f"## {text}"
    elif text_block['type'] == 4:  # image
        # validate image
        if 'metadata' not in text_block or 'id' not in text_block['metadata'] or re.findall(r'^0\*.{10,20}\.png', text_block['metadata']['id']) == None:
            raise ValueError(f'Block {text_block["id"]} has no image id or is not a png')
        image_url = f'https://miro.medium.com/{text_block["metadata"]["id"]}'
        text = f'![alt text]({image_url} "{text}")\n\n{text}'  # add a caption on hover and below
    elif text_block['type'] == 6 or text_block['type'] == 7:  # quote
        text = f'> {text}'
    elif text_block['type'] == 8:  # code block or quote, dont set language cuz we dont know it
        text = f"```\n{text}\n```"
    elif text_block['type'] == 9:  # bullet list
        text = f"* {text}"
    elif text_block['type'] == 10:  # numbered list
        if last_type == 10:  # if this is a continuation of a numbered list we have to backtrack to the previous find the current number
            k = 1
            while 1:
                if i-k > 0 and paragraphs_raw[i-k]['type'] == 10:
                    k += 1
                else:
                    break
            text = f"{k+1}. {text}"  # essentially we keep looking back 1 until we find the top of the numbered list to keep the function self contained
        else:
            text = f"1. {text}"  # if this is the first number we can just use 1 without checks

    elif text_block['type'] == 11:  # iframe, just post the thumbnail. TODO: actual embeds are going to be a bit more difficult
        if 'thumbnailurl' in text_block['iframe']:
            text = f'![alt text]({text_block["iframe"]["thumbnailurl"]} "{text}"'
        else:
            text = f'MEDIUM_IFRAME_RESOURCE_({text_block["iframe"]["mediaResourceId"]} "{text}"'
    elif text_block['type'] == 13:  # subtitle
        text = f"### {text}"
    elif text_block['type'] == 14:  # embedded link
        # here the text is actually already nicely in markdown format
        pass
    else:  # unknown type
        print(f'Unknown type {text_block["type"]} for id {text_block["name"]}')

    # finally we need to decide if we want 1, 2, or 3 newlines at the end
    if last_type == 9:  # 1 only if we have a sequential list
        text = f"{text}\n"
    elif text_block['type'] != 3:  # 2 is between paragraphs in the same section
        text = f"{text}\n\n"
    else:  # 2 is to seperae sections (i.e. new headers), was 3 but actually it renders the same soo
        text = f"{text}\n\n"

    return str(text)

# update article method - basically the ingestion method


def updateArticle(article_uuid):
    """ seperate function for job pooling """
    start = time.perf_counter()
    article: Content = Content.objects.get(uuid=article_uuid)

    postID = article.url.split('/')[-1].split('-')[-1]
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}  # lol idk it might work
    try:
        r = requests.get(f'https://medium.com/_/api/posts/{postID}', headers=headers)

        if not r.status_code == 200:  # unsuccessful request handling
            logger.error(f'Failed to get article {article.title}, status code {r.status_code}')
            if r.status_code == 410:  # gone
                logger.info(f'Article {article.title} is 410 gone, deleting')
                article.deleted = True
                article.save()
                return
            elif r.status_code == 429:  # we need to wait
                retry_time = int(r.headers['Retry-After'])
                logger.info(f'Article {article.title} is 429 throttled, retrying in {retry_time} seconds')
                time.sleep(retry_time)  # wait to retry, usually like an hour so its gonna be sitting here a while but thats fine
                # retry, print new headers for debug
                r = requests.get(f'https://medium.com/_/api/posts/{postID}', headers=headers)
                logger.debug(f'retried after 429, new headers are {r.headers}')
            else:
                return

        data = json.loads(r.text[16:])

        # if user deleted the article or their account then we mark it as deleted
        if data['success'] == False:
            logger.error(f'Failed to get article {article.url}, {data["error"]}')
            if 'deleted' in data['error']:  # though its possible we just got rate limited, so make sure to check the error
                article.deleted = True
                article.save()
            return
        else:
            article.deleted = False

        post = data['payload']['value']

        article.url = post['mediumUrl']
        article.title = post['title']
        article.last_response = data

        # author is annoying
        if 'references' in data['payload'] and 'User' in data['payload']['references']:
            article.author = data['payload']['references']['User'].popitem()[1]['name']
        elif '@' in article.url:
            article.author = article.url.split('@')[1].split('/')[0]

        article.subtitle = post['virtuals']['subtitle']
        article.thumbnail = f"https://miro.medium.com/{post['virtuals']['previewImage']['imageId']}"  # https://miro.medium.com/0*5avpGviF6Pf1EyUL.jpg
        article.content_read_seconds = int(float(post['virtuals']['readingTime'])*60)
        article.popularity['medium'] = {'totalClapCount': post['virtuals']['totalClapCount']}
        article.provider = 'medium'

        # NOTE: this is an example of a medium article but its actually a video https://medium.com/@digitalprspctv/vsco-style-images-in-3-simple-steps-photoshop-4de7e74b29c8

        # concat paragraphs
        paragraphs = []
        for par in post['content']['bodyModel']['paragraphs']:
            if par['type'] == 4:
                if '.gif' in article.thumbnail:  # we dont want gifs as preview, so if we happen to find an image to replace it in the body then we can use that instead
                    article.thumbnail = f"https://miro.medium.com/{par['metadata']['id']}"
            else:
                paragraphs.append(clean_str(par['text']))

        article.content = '\n\n'.join(paragraphs)

        # markdown time
        paragraphs_raw = data['payload']['value']['content']['bodyModel']['paragraphs']
        output = ""
        for i, text_block in enumerate(paragraphs_raw):
            text = medium_to_markdown(text_block, i, paragraphs_raw)
            output += text
        article.markdown = output

        # tags
        for t in post['virtuals']['tags']:
            if t['type'] == 'Tag':
                if t['slug'] not in article.tags:
                    article.tags.append(t['slug'])

        # we really hate gifs - also null out the default image, no point of keeping it
        if '.gif' in article.thumbnail or article.thumbnail == 'https://miro.medium.com/':
            article.thumbnail = None

        # get us an alternate thumbnail from our unsplash images library
        if hasattr(index, 'unsplash_photo_index') and (article.thumbnail_alternative is None or article.thumbnail_alternative_url is None):
            img = index.unsplash_photo_index.query(article.embedding_all_mpnet_base_v2, k=1, use_cached=False)[0][0]
            article.thumbnail_alternative = img
            article.thumbnail_alternative_url = img.photo_image_url

        # summarize if we dont have a summary yet
        if not ai.SUMMARIZER_CONFIG['MODEL_NAME'] in article.summary:
            # reduce to max tokens
            clean_text = article.content
            while len(ai.tokenizer(clean_text)['input_ids']) > ai.SUMMARIZER_CONFIG['MAX_TOKENS']:
                ten_percent = len(clean_text) // 10
                clean_text = clean_text[:-ten_percent]

            # logger.debug(f"{len(ai.tokenizer(clean_text)['input_ids'])} tokens")
            article.summary[ai.SUMMARIZER_CONFIG['MODEL_NAME']] = ai.summarizer(clean_text, min_length=ai.SUMMARIZER_CONFIG['MIN_LENGTH'], no_repeat_ngram_size=ai.SUMMARIZER_CONFIG['NO_REPEAT_NGRAM_SIZE'])[0]['summary_text']

        article.save()
        logger.info(f'Updated {article.title} in {time.perf_counter()-start:.3f}s')
    except Exception as e:
        err = str(e)
        logger.error(err)  # we do get banned if we have hit too fast - about 10 requests per second i think but not sure
        if 'Post was removed by the user' in err or 'Account is suspended' in err:
            article.deleted = True
            logger.error(f'Logging {article.title} as deleted')
            article.save()
