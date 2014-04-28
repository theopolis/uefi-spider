
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest

from uefispider.items import *

import json
import re
import copy
import os

lenovo_component = "1343112652574"
product_search = "http://support.lenovo.com/en_US/downloads/default/%s.ajax?%s"
product_select = "http://support.lenovo.com/en_US/downloads/default.page?%s"
download_select = "http://download.lenovo.com/lenovo/content/ddfm/%s-%s-%s.html"

'''
Usage:
scrapy crawl -a dump=/tmp/spiders LenovoSpider

Requirements:
innoextract, 7-zip, cabextract, unrar; are all helpful.

XML structure:
Properties->
  Data->
    Result->
      ProductSelectorResults->
        Options->
          [Option, value="id"].//text()=name
'''

def _search_url(tree):
    if len(tree) > 3: 
        return None
    select_types = ["getSeries", "getSubseries", "getMachineTypes"]
    selection = "-".join(tree)
    if len(tree) == 5:
        selection += "+" * 4
    else:
        selection += "-" * (5-len(tree))
    return product_search % (
        lenovo_component,
        "method=%s&productSelection=%s" % (select_types[len(tree)-1], selection)
    )

def _select_url(tree):
    if len(tree) > 3:
        return None
    query = {
        "submit": "true",
        "componentID": lenovo_component,
        "iwPreActions": "SetProduct",
        "prodId": "-".join(tree) + "--",
        "os": ""
    }
    ### This will set cookies and redirect, similar to HP.
    return product_select % "&".join(["%s=%s" % (k, v) for k, v in query.iteritems()])

def _download_url(series, subseries, product):
    return download_select % (series, subseries, product)

class LenovoSpider(UefiSpider):
    name = 'LenovoSpider'
    allowed_domains = [
        "lenovo.com",
    ]

    start_urls = [
        "http://support.lenovo.com/en_US/downloads/default.page"
    ]

    ### Hold a list of products/documents which are processed serially.
    #products = {}
    doc_ids = []

    def _get_results(self, response):
        sel = Selector(response)

        results = []
        options = sel.css("Properties").xpath("./Data/Result/ProductSelectorResults/Options/option")
        for option in options:
            value = option.xpath("./@value").extract()[0]
            name  = option.xpath("./text()").extract()[0]
            results.append((value, name))
        return results        

    def parse(self, response):
        series_list = ["P014"]

        for series in series_list:
            yield Request(url= _search_url([series]), callback= self.parse_series,
                meta= {"series": series, "dont_merge_cookies": True})


    def parse_series(self, response):
        results = self._get_results(response)
        series = response.meta["series"]

        ### Now we have a set of subseries IDs.
        for result in results:
            ###yield Request(url= _search_url([series, result[0]]), 
            yield Request(url= _search_url([series, "S006"]),
                callback= self.parse_subseries,
                meta= {"series": series, "subseries": result[0]})
            return

    def parse_subseries(self, response):
        results = self._get_results(response)
        series = response.meta["series"]
        subseries = response.meta["subseries"]

        for result in results:
            ###yield Request(url = _download_url(series, subseries, result[0]),
            yield Request(url= _download_url(series, "S006", "SS2500"),
                callback= self.parse_product,
                meta= {"cookiejar": result[1], "item_details": result},
                dont_filter= True)
            return

    def parse_product(self, response):
        def is_bios_update(name):
            #valid_names = ["BIOS Update"]
            valid_names = ["BIOS Update Utility"]
            ### The "utility" documents provide historic information.
            for valid in valid_names:
                if name.find(valid) >= 0:
                    return True
            return False

        sel = Selector(response)

        ### There's a lot of information on this page, but the update document
        ### repeats this information and includes historic data.
        updates = []
        rows = sel.css("#BIOS").css("#table1").xpath(".//tr")[1:]
        for row in rows:
            cells = row.xpath(".//td")
            name = cells[0].xpath("./text()").extract()[0]
            if not is_bios_update(name):
                ### This is not the droid we're looking for
                continue
            links = cells[0].xpath(".//a/@href").extract()
            updates.append(links[0])

        for update in updates:
            doc_id = update.split("DocID=")[1]
            ### Begin critical section
            if doc_id in self.doc_ids:
                continue
            self.doc_ids.append(doc_id)
            ### End critical section
            yield Request(url= update,
                callback= self.parse_document, 
                meta= {"item_details": response.meta["item_details"], "doc_id": doc_id})

        pass

    def parse_document(self, response):
        sel = Selector(response)

        systems = None
        changes = None
        uefi = False
        packages = None

        ### This is ugly!
        tables = sel.css(".v14-header-1")
        for table in tables:
            table_name = table.xpath("./text()").extract()[0]
            if table_name.find("Systems") > -1 and table_name.find("Operating") == -1:
                systems = table
            if table_name.find("Summary of Changes") > -1:
                changes = table
            if table_name.find("UEFI") > -1:
                uefi = True
            if table_name.find("Package") > -1:
                packages = table

        if not uefi:
            ### This is not a UEFI update.
            return

        ### Extract information for the current release from the downloads table.
        ### This information is NOT repeated in the version table below.
        downloads = sel.css(".downloadTable").xpath(".//tbody/tr")
        binary_url = downloads[0].xpath(".//td")[0].xpath(".//a/@href").extract()[0]
        notes_url = downloads[1].xpath(".//td")[0].xpath(".//a/@href").extract()[0]
        date = downloads[0].xpath(".//td")[3].xpath("./text()").extract()[0] 


        systems_list = []
        systems = systems.xpath("../../../following-sibling::ul")[0].xpath(".//li")
        for system in systems:
            systems_list.append(system.xpath("./text()").extract()[0])

        update_list = []
        updates = packages.xpath("../../..//tr")[1:]
        for i, update in enumerate(updates):
            cells = update.xpath(".//td")
            ### This format will be X.XX (NAME)
            version = cells[1].xpath("./text()").extract()[0].split("(")
            version = "%s (%s" % (version[0].strip(), version[1].strip()) 
            release = cells[3]
            #print version, release
            if i == 0:
                update_list.append((version, binary_url, notes_url))
                continue
            urls = release.xpath(".//a/@href").extract()
            update_list.append((version, urls[0], urls[1]))

        meta = {
            "systems": systems_list,
            "updates": update_list,
            "date": date,
            "url": response.url
        }

        yield Request(url= notes_url,
            callback= self.parse_notes,
            meta= meta)

    def parse_notes(self, response):
        ### This is a text-only document containing the versions and release notes.
        text = response.body.split("\r\n")

        dates_list = []
        release_notes = []

        document = response.meta

        line_num = 0
        scanning_changes = False
        scanning_version = None
        version_notes = []

        while line_num < len(text):
            line = text[line_num]
            line_num += 1

            ### Scan for "Package (ID)", next line is a set of delims, then updates until blank-line
            if line.find("Package (ID)") >= 0:
                line_num += 1
                for i in xrange(len(document["updates"])):
                    line = text[line_num]
                    line_num += 1
                    if len(line) == 0:
                        ### Problem!
                        break
                    version_info = line.split(" ")
                    dates_list.append(version_info[-1])
                continue

            ### While scan for "<" as first character
            ### Version <X.XX>, add lines until blank-line
            if line.find("Summary of Changes") >= 0:
                scanning_changes = True
            if scanning_changes:
                if len(line) == 0 and line_num <= len(text) and len(text[line_num]) == 0:
                    ### Double return, break
                    scanning_changes = False
                    continue
                if scanning_version and len(line) == 0:
                    ### Append and reset version notes.
                    scanning_version = False
                    release_notes.append(version_notes)
                    version_notes = []
                    continue
                if scanning_version:
                    version_notes.append(line.strip())
                    continue
                if len(line) > 0 and line[0] == "<":
                    scanning_version = True
                    continue
            pass

        ### Finally download the binaries
        for i, update in enumerate(document["updates"]):
            item = LenovoUpdateItem()
            item["url"] = document["url"]
            item["products"] = document["systems"]
            item["version"] = update[0]
            item["bios_url"] = update[1]
            item["notes_url"] = update[2]
            item["date"] = dates_list[i]
            item["desc"] = release_notes[i]
            item["item_id"] = update[0]

            yield Request(url= item["bios_url"],
                callback= self.parse_binary,
                meta= {"item": item})
        pass

    def parse_binary(self, response):
        item = response.meta["item"]
        item["binary"] = response.body
        item["binary_name"] = os.path.basename(response.url)

        yield item
        pass
