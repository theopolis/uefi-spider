
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest

from uefispider.items import *

import json
import re
import copy

json_headers = {
  "X-Requested-With": "XMLHttpRequest",
  "Accept": "application/json, text/javascript, */*",
}

class MsiSpider(UefiSpider):
    name = 'MsiSpider'
    allowed_domains = [
        "msi.com"
    ]

    start_urls = [
        "http://us.msi.com/download/pages/list_ajax"
    ]

    msi_search_vars = {
        "p": "service",
        "d": "list",
        "c": "download",
        "no": "",
        "cat": "mb",
        "pno": "",
        "switch": "ProductSelector",
        "sw": "ajax"
    }

    def _get_vars(self, no, pno):
        search_vars = copy.copy(self.msi_search_vars)
        search_vars["no"] = str(no)
        search_vars["pno"] = str(pno)
        return search_vars

    def parse(self, response):
        ### Generate a search for AMD and Intel chips
        intel_search = self._get_vars(170, 1)
        amd_search   = self._get_vars(171, 1)
        yield FormRequest(url= self.start_urls[0], method= "POST", headers= json_headers,
            formdata= intel_search, callback= self.parse_search)
        yield FormRequest(url= self.start_urls[0], method= "POST", headers= json_headers,
            formdata= amd_search, callback= self.parse_search)

    def parse_search(self, response):
        sel = Selector(response)

        ### Parse each sub-product type.
        searches = []
        product_selector = sel.css(".mr20").xpath("@no")
        if product_selector:
            pno = product_selector.extract()[0]

            products = sel.css(".ProdSel-item")
            for product in products:
                no = product.xpath("@no").extract()[0]
                searches.append((no, pno))
        #print searches

        ### Parse the actual products/boards.
        boards = []
        items = sel.css(".Prod-item")
        for item in items:
            title = item.xpath("@title").extract()[0]
            no = item.xpath("@no").extract()[0]
            boards.append((title, no))
        #print boards

        for sub_search in searches:
            search_vars = self._get_vars(sub_search[0], sub_search[1])
            yield FormRequest(url= self.start_urls[0], method= "POST", headers= json_headers,
                formdata= search_vars, callback= self.parse_search)

        for board in boards:
            url = "http://us.msi.com/product/mb/%s.html" % board[0]
            item = MsiUpdateLinkItem()
            item["id"] = board[1]
            item["title"] = board[0]
            item["url"] = url

            yield Request(url= "%s#/?div=BIOS" % url, callback= self.parse_board, 
                meta= {"attrs": item})
        pass

    def parse_board(self, response):
        def extract_field(field_sel):
            return field_sel.xpath(".//text()").extract()[0]
        sel = Selector(response)

        updates = []
        update_sels = sel.css(".div-BIOS").css(".table_gray")
        for update in update_sels:
            item = MsiUpdatePageItem()
            fields = update.css("td")
            item["desc"] = extract_field(fields[2])
            item["version"] = extract_field(fields[4])
            item["driver_type"] = extract_field(fields[6])
            item["date"] = extract_field(fields[8])
            try:
                item["bios_url"] = fields[10].xpath(".//a/@href").extract()[0]
            except Exception, e: 
                #print response.meta["attrs"]["title"], str(e)
                continue
            item["binary_name"] = item["bios_url"].split("/")[-1]
            item["item_id"] = item["binary_name"].split(".", 1)[0]
            item["attrs"] = dict(response.meta["attrs"])
            updates.append(item)

        for update in updates:
            yield Request(url= update["bios_url"], callback= self.parse_binary, 
                meta= {"item": update})
            
    def parse_binary(self, response):
        item = response.meta["item"]
        item["binary"] = response.body

        yield item


