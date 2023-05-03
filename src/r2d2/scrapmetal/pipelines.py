# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import shelve
import time


class ScrapmetalPipeline:
    def open_spider(self, spider):
        filename = "d2_export_{}.db".format(int(time.time()))
        self.db = shelve.open(filename, 'c')

    def close_spider(self, spider):
        self.db.close()

    def process_item(self, item, spider):
        key = item["url"]
        self.db[key] = item
        self.db.sync()
        return item
