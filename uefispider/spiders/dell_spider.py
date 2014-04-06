
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import Request

from uefispider.items import *

import json
import re

#from scrapy.shell import inspect_response
#inspect_response(response)

class DellSpider(UefiSpider):
  name = 'DellSpider'
  allowed_domains = [
    "search.dell.com", 
    "www.dell.com",
    "dell.com"
    #"downloadmirror.intel.com",
    #"search.intel.com",
  ]

  dell_search_vars = {
    "c":       "us",     # country
    "l":       "en",     # language
    "s":       "gen",    # search type (home, business, generic)
    "cat":     "sup",
    "k":       "BIOS",   # input
    "rpp":     "20",     # results per-page? does not change
    "p":       "1",      # page index
    "subcat":  "dyd",
    "rf":      "all",
    "nk":      "f",
    "sort":    "K",
    "nf":      "catn~BI",
    "navla":   "catn~BI",
    "ira":     "False",
    "~srd":    "False",
    "ipsys":   "False",
    "advsrch": "False",
    "~ck":     "anav"
  }

  filetype_blacklist = ["txt", "sign", "pdf"]

  results_url = "http://search.dell.com/results.aspx?%s"
  start_urls = [
    results_url % 
      ("&".join(["%s=%s" % (k, v) for k, v in dell_search_vars.iteritems()]))
  ]

  ### List of crawled item IDs
  item_ids = []

  def _get_item_id(self, url):
    driver_id = url.find("driverId=")
    item = url[driver_id + len("driverId="):]
    if item.find("&") >= 0:
      item = item[:item.find("&")]
    return item

  def parse(self, response):
    sel = Selector(response)

    page_number = int(self.dell_search_vars["p"])
    print "Debug: On Page %d" % page_number

    total_regex = r".* (\d+) Results"
    total_results = sel.css(".PaginationCtrlResltTxt")
    if len(total_results) < 1:
      ### Cannot determine the number of search results
      print "Error: cannot determine search results."
      return 

    total_string = total_results.extract()[0]
    total_match = re.search(total_regex, total_string)
    if total_match is None:
      print "Error: cannot determine search results."
      return

    ### It turns out this is just a guestimate by Dell, let's double it?!
    total_results = int(total_match.group(1)) #* 2
    ### There's 20 results per page, and I cannot change this!?
    total_pages = (total_results / 20) + 1

    ### Parse this initial page's results.
    for result in self.parse_results(response):
      yield result

    for page in xrange(2, total_pages):
      self.dell_search_vars["p"] = str(page)
      yield Request(
        url= self.results_url % 
          ("&".join(["%s=%s" % (k, v) for k, v in self.dell_search_vars.iteritems()])),
        callback= self.parse_results)
    pass

  def parse_results(self, response):
    ### Parse update results from search page, yield the links to the updates
    sel = Selector(response)
    drivers = sel.css("div.driver_container")
    if len(drivers) == 0:
      ### No items on this page
      print "Debug: reached the end."
      return

    result_items = []
    for driver in drivers:
      result_item = DellBiosUpdateLinkItem()
      compatibility = driver.css("input.hdnCompProduct").xpath("@value")
      if len(compatibility) != 0:
        ### Compatibility tells us the model and thus mainboard/config.
        systems = compatibility.extract()[0].strip().split("#")
        result_item["compatibility"] = []
        for system in systems:
          if sytem.find("DesktopLatitudeOptiplexPrecisionVostro") >= 0:
            result_item["compatibility"].append("XPS Notebook R720")
          else:
            result_item["compatibility"].append(system.strip())

      url = driver.css("input.hdnDriverURL").xpath("@value")
      if len(url) == 0:
        print "ERROR: No URL for update?"
        continue
      ### Driver type is saved as a sanity check.
      result_item["url"] = url.extract()[0]
      details = driver.css("div.driver_detail::text").extract()
      result_item["driver_type"] = details[0][2:]
      ### Release date only includes the date, the previous versions include a timestamp.
      result_item["release_date"] = details[1][2:]
      result_items.append(result_item)

    for item in result_items:
      item_id = self._get_item_id(item["url"])
      ### Do not attempt duplicate update parsing.
      if item_id in self.item_ids:
        continue
      yield Request(url= item["url"], meta= {"result_item": item}, callback= self.parse_update)
    pass

  def parse_update(self, response):
    sel = Selector(response)

    ### There may be multiple downloads, the link is held in a javascript call.
    notes_link = ""
    driver_links = sel.css("#GetDriver").xpath("@href")
    if len(driver_links) == 0:
      raise Exception("Debug: No driver links found.")
    try:
      driver_links = [link.split(",")[1].strip("' ") for link in driver_links.extract()]
    except Exception, e:
      raise Exception("Error: cannot extract links. (%s)" % str(e))

    ### Save the release link separately (if it exists).
    for link in driver_links:
      if link.find("Release") >= 0 and link[-3:] == "txt":
        notes_link = link

    driver_names = sel.css("p.DriverDetails_FileFormat_Names::text")
    if len(driver_names) == 0:
      raise Exception("Debug: No driver names found.")
    driver_names = driver_names.extract()

    ### Update version provided in header.
    version = sel.css("a#dellVendorVersionToolTipId::text").extract()[0]

    ### There is inconsistency in naming previous versions, which may include spaces and commas.
    previous_versions = []
    pversions = sel.css("a#Versions")
    for pversion in pversions:
      version_name = "".join([c for c in pversion.xpath("text()").extract()[0] if c not in [",", " "]])
      version_link = "http://www.dell.com/%s" % pversion.xpath("@href").extract()[0].split("&", 1)[0]
      version_date = pversion.xpath("../../following-sibling::td/text()").extract()[0].strip()
      version_id   = version_link[version_link.find("driverId=") + len("driverId="):]
      previous_versions.append((version_name, version_link, version_date, version_id))

    #print previous_versions
    importance = "Unknown"
    fixes = ""

    ### Parse optional importance label and fixes/enhancement content.
    expands = sel.xpath("//h3")
    for expand in expands:
      expand_text = expand.css("::text").extract()[0]
      if expand_text.find("Level of Importance") == 0:
        importance = expand_text[expand_text.find(":")+1:]
      if expand_text.find("Fixes") == 0:
        try:
          expand_body = expand.xpath(".//following-sibling::div")[0].\
            css(".DriverDetails_RowData::text").extract()
          fixes = expand_body[0]
        except Exception, e:
          print e
          pass
      if expand_text.find("Compatibility") == 0:
        system_set = expand.xpath("./following-sibling")

    item = DellBiosUpdatePageItem()
    item["notes_url"] = notes_link
    item["bios_urls"] = [l for l in driver_links if l.split(".")[-1] not in self.filetype_blacklist]
    item["file_names"] = [n for n in driver_names if n.split(".")[-1] not in self.filetype_blacklist]
    item["previous_versions"] = previous_versions
    item["version"] = version
    item["importance"] = importance
    item["fixes"] = fixes
    #item["attrs"] = dict(response.meta["result_item"])

    link_item = response.meta["result_item"]

    ### Try to get date (again)
    details = sel.css(".DriverDetails_Table_ItemLabel")
    if len(details) > 0:
      date = details[0].xpath("./following-sibling::td/text()").extract()
      if len(date) > 0:
        link_item["release_date"]
    item["attrs"] = dict(link_item)

    ### Set the item ID as the driver/update link ID.
    item["item_id"] = self._get_item_id(item["attrs"]["url"])
    self.item_ids.append(item["item_id"])

    for i in xrange(len(item["bios_urls"])):
      if item["bios_urls"][i].split(".")[-1].lower() != "exe":
        continue
      ### Download each file associated
      yield Request(url= item["bios_urls"][i], callback= self.parse_binary,
        meta= {"name": item["file_names"][i], "item_id": item["item_id"]})
      ### For now, only download the first exe.
      break

    ### Crawl the update versions (may be duplicates) for this system
    for update in previous_versions:
      update_item = DellBiosUpdateLinkItem()
      update_item["url"] = update[1]
      update_item["release_date"] = update[3]
      update_item["compatibility"] = link_item["compatibility"]
      update_item["desc"] = link_item["desc"]
      yield Request(url= update[1], meta= {"result_item": update_item}, 
        callback= self.parse_update)

    yield item
    pass

  def parse_binary(self, response):
    item = BinaryItem()
    item["binary"] = response.body
    item["binary_name"] = response.meta["name"]
    item["item_id"] = response.meta["item_id"]

    yield item

