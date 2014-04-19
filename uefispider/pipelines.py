# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import os

from uefispider.items import *

class UefispiderPipeline(object):
    def process_item(self, item, spider):
        spider_name = spider.name
        item_id = item["item_id"]

        print spider.output, spider_name, item_id
        output_dir = os.path.join(spider.output, spider_name, item_id)
        
        binary = item["binary"] if "binary" in dict(item) else ""
        item["binary"] = ""

        binary_name = "uefi.bin"
        if "binary_name" in dict(item):
            binary_name = item["binary_name"]

        try:
            os.makedirs(output_dir)
        except Exception, e:
            print "Cannot make directories (%s). (%s)" % (output_dir, str(e))

        try:
            if type(item) is not BinaryItem:
                ### Only write JSON if this is not a binary-only item.
                data = json.dumps(dict(item))
                with open(os.path.join(output_dir, "details.json"), "w") as fh:
                    fh.write(data)

            if len(binary) > 0:
                ### An item may only include meta data.
                with open(os.path.join(output_dir, binary_name), "wb") as fh:
                    fh.write(binary)
        except Exception, e:
            print "Cannot write data (%s). (%s)" % (output_dir, str(e))

        #return item
