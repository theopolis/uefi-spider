# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

from scrapy.spider import Spider
import os

class UefiSpider(Spider):
  name = 'UefiSpider'

  def __init__(self, output= 'output'):
    self.output = output
    if self.output[0] != '/':
      self.output = os.path.join(os.getcwd(), self.output)