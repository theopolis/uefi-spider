# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field

class UefispiderItem(Item):
    item_id = Field()
    binary = Field()
    pass

class IntelBiosUpdateLinkItem(UefispiderItem):
    url = Field()
    name = Field()
    date = Field()
    version = Field()
    desc = Field()
    status = Field()

class IntelBiosUpdatePageItem(UefispiderItem):
    bios_url = Field()
    notes_url = Field()
    products = Field()
    attrs = Field()