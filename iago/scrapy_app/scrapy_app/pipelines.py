# Item pipelines
# https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import logging
from v0.models import Content

logger = logging.getLogger(__name__)

class ScrapyAppPipeline(object):
    def __init__(self, *args, **kwargs):
        self.articleCount = 0

    def close_spider(self, spider):
        # And here we are saving our crawled data with django models

        # Article.objects.bulk_create(self.articles)
        logger.info(f'-- {str(spider.name).upper()} SPIDER FINISHED WITH {str(self.articleCount)} ARTICLES ADDED')

    def process_item(self, item, spider):
        article:Content = item['article']
        article.save()
        self.articleCount += 1
        return item
