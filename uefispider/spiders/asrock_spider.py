
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest

from uefispider.items import *

import json
import re
import copy

class AsrockSpider(UefiSpider):
    name = 'AsrockSpider'
    allowed_domains = [
        "asrock.com",
        "66.226.78.22"
    ]

    start_urls = [
        "http://www.asrock.com/support/download.asp?c=All"
    ]

    def parse(self, response):
        sel = Selector(response)

        machines = []
        rows = sel.css("tr")
        for row in rows:
            bgcolor = row.xpath("@bgcolor")
            if not bgcolor or len(bgcolor) == 0:
                continue
            bgcolor = bgcolor.extract()[0]
            if bgcolor not in ["white", "#e8e8e8"]:
                continue
            cells = row.css("td")
            chipset = cells[0].xpath(".//text()").extract()[0]
            if chipset in ["Chipset"]:
                continue
            name = cells[1].xpath(".//text()").extract()[0]
            link = cells[1].css("a").xpath("@href").extract()[0]
            #print chipset, name, link
            item = AsrockLinkItem()
            item["chipset"] = chipset
            item["product"] = name
            item["url"] = "http://www.asrock.com%s" % link

            machines.append(item)

        for machine in machines:
            yield Request(machine["url"], callback= self.parse_machine,
                meta= {"item": machine})

    def parse_downloads(self, response):
        def extract_field(field_sel):
            return field_sel.xpath(".//text()").extract()[0]
        sel = Selector(response)

        updates = []
        rows = sel.css("tr")
        for row in rows:
            cells = row.css("td")
            if len(cells) != 10:
                continue
            item = AsrockUpdateItem()
            item["version"] = extract_field(cells[0])
            item["date"] = extract_field(cells[1])
            item["bios_type"] = extract_field(cells[2])
            if item["bios_type"] not in ["Instant Flash"]:
                continue
            item["desc"] = extract_field(cells[4])
            item["bios_url"] = cells[8].css("a").xpath("@href").extract()[0]
            item["binary_name"] = item["bios_url"].split("/")[-1]
            item["item_id"] = item["binary_name"].replace(".zip", "")

            item["attrs"] = dict(response.meta["item"])
            #print dict(item)
            updates.append(item)

        for update in updates:
            yield Request(url= update["bios_url"], callback= self.parse_binary,
               meta= {"item": update})
            pass
        pass

    def parse_machine(self, response):
        sel = Selector(response)

        download_link = None
        list_items = sel.css("#LeftMenu").css("li")
        for item in list_items:
            text = item.xpath(".//text()").extract()[0]
            if text.find("Download") < 0:
                continue
            try:
                download_link = item.css("a").xpath("@href").extract()[0]
            except:
                continue

        if download_link is not None:
            yield Request(url= "http://www.asrock.com%s&os=BIOS" % download_link, 
                callback= self.parse_downloads,
                meta= {"item": response.meta["item"]})
        pass

    def parse_binary(self, response):
        item = response.meta["item"]
        item["binary"] = response.body

        yield item
