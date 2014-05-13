
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest

from uefispider.items import *
from urlparse import urlparse

import json
import sys
import os

base_search   = "http://www.gigabyte.us:80/support-downloads/category-level_ajax.aspx?%s"
submit_search = "http://www.gigabyte.us/support-downloads/download-center_ajax.aspx?%s"
bios_search   = "http://www.gigabyte.us/products/product-page_ajax.aspx?%s"

def _search_url(ck, lev, val):
    return base_search % ("ck=%s&lev=%s&val=%s" % (ck, lev, val))

def _submit_url(p, ck, pid):
    ### p=1&kw=&ck=2&pid=3752
    return submit_search % ("p=%s&kw=&ck=%s&pid=%s" % (str(p), ck, pid))

def _bios_url(pid):
    #return bios_search % ("t=dl&pid=%s&dlt=%s&cg=%s&ck=%s&h=bios&MDA2=" % (
    #    pid, dlt, cg, ck
    #))
    return bios_search % ("t=dl&pid=%s&dlt=2" % pid)
    pass

def _url_params(url):
    url = urlparse(url)
    params = {p.split("=")[0]: p.split("=")[1] for p in url.query.split("&")}
    return params

class GigabyteSpider(UefiSpider):
    name = 'GigabyteSpider'
    allowed_domains = [
        "gigabyte.us",
    ]

    start_urls = [
        ### Motherboards
        _search_url(2, 1, 2),
        _search_url(101, 1, 101),
        _search_url(112, 1, 112),
        ### Notebook/Netbook
        _search_url(5, 1, 5),
        ### Slate PC (tablet)
        _search_url(71, 1, 71),
        ### Set top boxes
        _search_url(131, 1, 131),
        _search_url(133, 1, 133),
        ### Barebones
        _search_url(102, 1, 102),
        _search_url(122, 1, 122),
        ### NAS
        _search_url(132, 1, 132),
    ]

    def parse(self, response):
        ### Each search returns a JSON response of Rows (classes of products)
        try:
            json_response = json.loads(response.body)
        except Exception, e:
            print "Cannot load JSON from category search."
            return

        params = _url_params(response.url)
        level = params["lev"] if "lev" in params else "0"

        if "ck" not in params:
            print "Cannot find CK value in response params?"
            return
        if "node" not in json_response:
            print "Cannot find NODE value in response response?"

        for row in json_response["rows"]:
            if row["value"] == "":
                continue
            ### node=1 indicates a bottom-level search, each row is an item.
            if json_response["node"] == "0":
                yield Request(url= _search_url(params["ck"], int(level)+1, row["value"]))
            else:
                yield Request(url= _submit_url(1, params["ck"], row["value"]), 
                    callback= self.parse_submit)
        pass

    def parse_product(self, response):
        sel = Selector(response)

        results =  sel.css(".tbl_driver")
        if not results:
            return

        rows = results.css("tr")
        for i in xrange(len(rows)-1):
            data = rows[i+1].css("td")
            ### Most common (no bios) will not include results
            if len(data) == 0:
                continue
            item = GigabyteUpdateItem()
            ### DLT=2 may be mapped differently.
            try:
                item["version"] = data[0].xpath(".//text()").extract()[0]
            except Exception, e:
                continue

            item["date"] = data[2].xpath(".//text()").extract()[0]
            links = data[3].css("a")
            ### Links may be malformed.
            if len(links) < 3:
                continue
            item["bios_url"] = data[3].css("a")[2].xpath("@href").extract()[0]
            ### Handle a lack-of-desc.
            try:
                item["desc"] = data[4].xpath(".//text()").extract()[0]
            except Exception, e:
                item["desc"] = ""
            #print item_id, response.url
            #print version, date, bios_url, desc
            basename = os.path.basename(urlparse(item["bios_url"]).path)
            item["item_id"] = os.path.splitext(basename)[0]
            item["binary_name"] = basename
            item["attrs"] = dict(response.meta["item"])

            yield Request(url= item["bios_url"], callback= self.parse_binary,
                meta= {"item": item})
        pass

    def parse_submit(self, response):
        ### After navigating the search menus, parse a list of results.
        sel = Selector(response)

        results = sel.css("tr")
        for result in results:
            item = GigabyteLinkItem()
            item["driver_type"] = result.css(".text2").xpath(".//text()").extract()[0]
            item["name"] = result.css(".title3").css("a").xpath(".//text()").extract()[0]
            item["url"] = result.css(".title3").css("a").xpath("@href").extract()[0]
            params = _url_params(item["url"])
            yield Request(url= _bios_url(params["pid"]),
                callback= self.parse_product,
                meta= {"item": item})
        pass

    def parse_binary(self, response):
        item = response.meta["item"]
        item["binary"] = response.body

        yield item

