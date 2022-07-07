import logging
import time

import pytesseract
from iago.settings import BASE_DIR, LOGGING_LEVEL_MODULE
from pdf2image import convert_from_bytes

from v0 import ai, index
from v0.models import Content
from v0.utils import mediumReadtime, truncateTextNTokens

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL_MODULE)


def ingestContentPDF(content: Content):
    """
    Ingests content from a PDF file.
    """
    start = time.perf_counter()

    # convert pdf to list of PIL images
    try:
        pages = convert_from_bytes(content.file.read())
        logger.debug(f'{content.title} is a valid pdf')
    except SyntaxWarning:
        content.type = Content.types.invalid_file
        content.save()
        logger.warning(f'{content.title} is an invalid pdf')
        return

    logger.debug(f'sent from File ingestion to OCR in {time.perf_counter()-start:.3f}s')

    # get text from pages
    content.content = ''
    for page in pages:
        content.content = content.content + pytesseract.image_to_string(page, lang='eng', config=f'--oem 1 --tessdata-dir {str(BASE_DIR/"tesseract/")}') # we have the lang file locally, we currently use lstm eng fast

    # clear memory
    del pages

    # populate the rest of the fields
    content.content_read_seconds = mediumReadtime(content.content) # NOTE might be messed up because of all the newlines
    # lol i know that the express api sorts by popularity on medium articles so this is my hack to get to the front of the line
    content.popularity['medium'] = {'totalClapCount': 9999999999}

    # ai stuff
    # embed
    content.embedding_all_mpnet_base_v2 =  list(ai.embedding_model.encode([content.content], use_cache=False)[0])

    # summarize
    # reduce to max tokens
    trunc_text, num_tokens = truncateTextNTokens(content.content)
    content.summary[ai.SUMMARIZER_CONFIG['MODEL_NAME']] = ai.summarizer(trunc_text, min_length=ai.SUMMARIZER_CONFIG['MIN_LENGTH'], no_repeat_ngram_size=ai.SUMMARIZER_CONFIG['NO_REPEAT_NGRAM_SIZE'])[0]['summary_text']

    # thumbnail
    img = index.unsplash_photo_index.query(content.embedding_all_mpnet_base_v2, k=1, use_cached=False)[0][0]
    content.thumbnail_alternative = img
    content.thumbnail_alternative_url = img.photo_image_url

    # skills
    skills, rankings, query_vector = index.skills_index.query(content.embedding_all_mpnet_base_v2, k=5, min_distance=.21)
    content.skills.set(skills)

    content.save()
    return content
