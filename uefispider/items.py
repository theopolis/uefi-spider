# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field

class UefispiderItem(Item):
    item_id = Field()
    binary = Field()
    binary_name = Field()
    pass

class BinaryItem(UefispiderItem):
    ### This item will only write a binary object.
    binary_name = Field()
    pass

class GigabyteLinkItem(UefispiderItem):
    driver_type = Field()
    url = Field()
    name = Field()

class GigabyteUpdateItem(UefispiderItem):
    version = Field()
    date = Field()
    desc = Field()
    bios_url = Field()
    attrs = Field()

class LenovoUpdateItem(UefispiderItem):
    version = Field()
    date = Field()
    desc = Field()
    bios_url = Field()
    url = Field()
    products = Field()
    notes_url = Field()

class AsrockLinkItem(UefispiderItem):
    chipset = Field()
    product = Field()
    url = Field()

class AsrockUpdateItem(UefispiderItem):
    version = Field()
    date = Field()
    desc = Field()
    bios_type = Field()
    bios_url = Field()
    attrs = Field()

class MsiUpdateLinkItem(UefispiderItem):
    url = Field()
    title = Field()
    id = Field()

class MsiUpdatePageItem(UefispiderItem):
    desc = Field()
    driver_type = Field()
    bios_url = Field()
    version = Field()
    date = Field()
    attrs = Field()

class HPBiosUpdateLinkItem(UefispiderItem):
    url = Field()
    date = Field()
    name = Field()

class HPBiosUpdatePageItem(UefispiderItem):
    bios_url = Field()
    notes_url = Field()
    version = Field()
    download_name = Field()
    attrs = Field()

    ### From revision history
    previous_versions = Field()

    ### From a textual-update
    importance = Field()
    compatibility = Field()
    ssm = Field() # remote update
    desc = Field()
    fixes = Field()

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
    attrs = Field() # attributes from LinkItem

class DellBiosResultsItem(Item):
    total = Field()

class DellBiosUpdateLinkItem(UefispiderItem):
    url = Field()
    release_date = Field()
    driver_type = Field()
    compatibility = Field()
    desc = Field()

class DellBiosUpdatePageItem(UefispiderItem):
    bios_urls = Field()
    file_names = Field()
    notes_url = Field()
    previous_versions = Field()
    importance = Field()
    version = Field()
    fixes = Field()
    attrs = Field() # attributes from LinkItem
