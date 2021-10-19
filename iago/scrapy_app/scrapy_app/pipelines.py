# Item pipelines
# https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from action_engine.models import Article
from django.db import models

logger = logging.getLogger(__name__)

class ScrapyAppPipeline(object):
    def __init__(self, *args, **kwargs):
        self.articles = set()

    def close_spider(self, spider):
        # And here we are saving our crawled data with django models

        # Article.objects.bulk_create(self.articles)
        logger.info(f'-- {str(spider.name).upper()} SPIDER FINISHED WITH {str(len(self.articles))} ARTICLES ADDED')

    def process_item(self, item, spider):
        article = Article()

        article.title = item['title']
        article.content = item['content']
        article.url = item['url']
        
        article.save()
        self.articles.add(article)
        
        return item
