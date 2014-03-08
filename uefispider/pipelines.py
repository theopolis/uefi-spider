# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import os

class UefispiderPipeline(object):
    def process_item(self, item, spider):
        spider_name = spider.name
        item_id = item["item_id"]

        print spider.output, spider_name, item_id
        output_dir = os.path.join(spider.output, spider_name, item_id)
        
        binary = item["binary"]
        item["binary"] = ""
        #del item["binary"]

        try:
          os.makedirs(output_dir)
        except Exception, e:
          print "Cannot make directories (%s). (%s)" % (output_dir, str(e))

        try:
          data = json.dumps(dict(item))
          with open(os.path.join(output_dir, "details.json"), "w") as fh:
            fh.write(data)

          with open(os.path.join(output_dir, "uefi.bin"), "wb") as fh:
            fh.write(binary)
        except Exception, e:
          print "Cannot write data (%s). (%s)" % (output_dir, str(e))

        #return item
