
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest
from scrapy.http.cookies import CookieJar

from uefispider.items import *

import json
import re
import urllib
import sys

#from scrapy.shell import inspect_response
#inspect_response(response)

class HPSpider(UefiSpider):
  name = 'HPSpider'
  allowed_domains = [
    "www2.hp.com",
    "hp.com"
  ]

  cookies = {
    "HP_SPF_HOST":      "h20566.www2.hp.com",
    "HP_SPF_LOCALE":    "en-US",
    "HP_SPF_SITE":      "hpsc",
  }

  download_url = "http://ftp.hp.com/pub/softpaq/sp%d-%d/%s"

  start_urls = [
    "http://h20566.www2.hp.com/portal/site/hpsc/template.PAGE/public/kb/search/"
  ]

  crawled_items = {}
  #crawled_searches = []
  ### Store all of the crawled search results

  def _get_download_link(self, filename, sp_number= None):
    ### An update file name may include a distinct "SP" number.
    if sp_number is None:
      sp_number = filename

    update_id = sp_number[2:sp_number.find(".")]
    try:
      update_id = int(update_id)
      url = self.download_url % (1 + (update_id/500)*500, (update_id/500)*500 + 500, filename)
    except Exception, e:
      ### Cannot parse the filename, was an sp_number provided?
      url = None
    return url

  def _get_update_id(self, update_link):
    index = update_link.find("swItem%253D") + len("swItem%253D")
    end_tok = [update_link.find("&", index), update_link.find("%25", index)]
    if end_tok[0] >= 0 and end_tok[1] >= 0:
      end_tok = min(end_tok[0], end_tok[1])
    elif end_tok[0] >= 0: end_tok = end_tok[0]
    else: end_tok = end_tok[1]
    update_id = update_link[index: end_tok]
    return update_id
    pass

  def _write_results(self):
    print "Debug: Finished reading search results, writing."
    with open("hp-output.json", 'w') as fh:
      fh.write(json.dumps([dict(item) for i, item in self.crawled_items.iteritems()]))
    return

  def parse(self, response):
    ### The initial hit of the search page, generate all additional searches, accept the cookies and begin.
    months = range(0, 12)         # Month is 0-counted
    years  = range(2006, 2014+1)  # Years is actual-counted

    monthly_searches = []
    for year in years:
      for month in months:
        end_year = year if month != 11 else year+1
        end_month = month+1 if month != 11 else 0
        #print (month, year, end_month, end_year)
        monthly_searches.append((year, month, end_year, end_month))

    response.meta["searches"] = monthly_searches
    return self.parse_begin(response)

  def parse_begin(self, response):
    ### Hit the page we were redirected to with the cookies set.

    return Request(url = response.url, cookies= self.cookies, 
      meta= {"searches": response.meta["searches"]}, 
      callback= self.parse_accept)

  def parse_accept(self, response):
    ### At the search form, begin to generate monthly searches, alert if >100 results.
    sel = Selector(response)

    ### This will select the REAL url (with appended query string "tokens").
    url_path = ""
    forms = sel.xpath("//form")
    for form in forms:
      form_ids = form.xpath("@id").extract()
      if len(form_ids) == 0: 
        continue
      if form_ids[0] == "refineSearchForm":
        url_path = form.xpath("@action").extract()[0]

    ### The search load-balances
    domain = response.url[len("http://"):response.url.find(".")]

    url = "http://%s.www2.hp.com/%s"
    form_data = {
      "didYouMean": "",
      "searchCrit": "allwords",
      "docType":"Drivers",
      #"docType":"Patch",
      "dateRange":"all",
      "dateSearchType":"dateRange",
      "startDateYear": None,
      "startDateMonth": None,
      "startDateDay": "1",
      "endDateYear": None,
      "endDateMonth": None,
      "endDateDay":"1",
      "resPerPage":"100",
      "sortCrit":"date",
      "showSummary":"yesX",
      "calledBy":"Search_Main",
      "mode":"text",
      "searchString":"BIOS Update",
      "searchRes":"Search",
      "advSearchFlag":"true",
    }

    ### Pull off the remaining searchs, and fill in vars for the 'next' search.
    remaining_searches = response.meta["searches"]

    form_data["startDateYear"] = str(remaining_searches[0][0])
    form_data["startDateMonth"] = str(remaining_searches[0][1])
    form_data["endDateYear"] = str(remaining_searches[0][2])
    form_data["endDateMonth"] = str(remaining_searches[0][3])

    return FormRequest(url= url % (domain, url_path) + "&month=%d&year=%d" % (remaining_searches[0][1], remaining_searches[0][0]), 
      headers= {"Content-Type": "application/x-www-form-urlencoded"},
      formdata= form_data, method= "POST", cookies= self.cookies,
      meta= {"searches": remaining_searches[1:], "this": (form_data["startDateYear"], form_data["startDateMonth"], form_data["endDateYear"], form_data["endDateMonth"])},
      dont_filter= True,
      callback= self.parse_search)
    pass

  def parse_search(self, response):
    ### The search results
    sel = Selector(response)

    results = sel.css("table[title='Search Results Index']").xpath(".//tr")[1:]
    if len(results) == 100:
      ### The search will only return 100 results.
      ### If 100 is reached, the search must be repeated with better accuracy.
      #raise Exception("Reached 100 results, day-granularity not implemented.")
      with open('overflow_months.log', 'a+') as fh: 
        fh.write('%s %s %s %s\n' % (response.meta["this"][0], response.meta["this"][1], response.meta["this"][2], response.meta["this"][3]))
      print "Reached 100 results, consider day-granularity."

    print ""
    print "RESULTS: %d" % len(results)
    print response.meta["searches"]
    print ""

    #items = []
    for result in results:
      download_type = "".join(result.xpath(".//td")[2].xpath(".//text()").extract()).strip()
      if download_type != "BIOS":
        continue

      item = HPBiosUpdateLinkItem()
      item["url"]  = "".join(result.xpath(".//td")[1].xpath(".//a/@href").extract()).strip()
      item["name"] = "".join(result.xpath(".//td")[1].xpath(".//a//text()").extract())
      item["date"] = "".join(result.xpath(".//td")[3].xpath(".//text()").extract())

      item["item_id"] = self._get_update_id(item["url"])

      if item["item_id"] in self.crawled_items:
        #raise Exception("Found duplicate: (%s, %s, %s)" % (item["item_id"], item["name"], item["date"]))
        print "Found duplicate: (%s, %s, %s)" % (item["item_id"], item["name"], item["date"])
        continue
      ### Store the item in the object-global item stash.
      self.crawled_items[item["item_id"]] = item
      #items.append(item)

    remaining_search_count = len(response.meta["searches"])
    if remaining_search_count > 0:
      ### The are more searches, repeat.
      yield Request(url= self.start_urls[0], #+ "?%d" % remaining_search_count, 
        meta= {"searches": response.meta["searches"]}, 
        dont_filter= True,
        callback= self.parse_accept)
      return

    ### Debugging, make this an argument/option later
    self._write_results()

    ### The searches are complete, parse responses.
    for item_id, item in self.crawled_items.iteritems():
      #callback = self.parse_me_update if item["name"].find("ME Firmware Update") >= 0 else self.parse_update
      callback = self.parse_update
      yield Request(url= item["url"], callback= callback, meta= {"result_item": item})
      
  def parse_update(self, response):
    ### The update (download) page for the BIOS.

    #if response.body.find("does NOT include a System BIOS image") >= 0:
    #  ### Intel ME drivers are sometimes classified as BIOS updates.
    #  return self.parse_me_update(response)

    sel = Selector(response) 

    fields = sel.css("table.m10").xpath(".//tr/td")
    version = fields[1].xpath(".//text()").extract()[0]
    version = version[:version.find("(")].strip()

    name = fields[3].xpath(".//text()").extract()[0]
    name = name[:name.find("(")].strip()

    ### Try to parse the "name" as an "SP" number
    download_link = self._get_download_link(name)

    item = HPBiosUpdatePageItem()
    item["bios_url"] = download_link
    item["version"] = version
    item["binary_name"] = name
    item["attrs"] = dict(response.meta["result_item"])
    item["item_id"] = item["attrs"]["item_id"]

    ### Updates have their description in different tabs
    tab_names = {}
    tabs = sel.css("tr#device-nav").xpath(".//td")
    for i, tab in enumerate(tabs):
      tab_name = " ".join(tab.xpath(".//text()").extract()).lower()
      tab_link = "".join(tab.xpath(".//a/@href").extract())
      tab_names[tab_name] = tab_link

    ### Set the release notes url, this may be optional?
    item["notes_url"] = tab_names["release notes"] if "release notes" in tab_names else None

    if "revision history" in tab_names:
      ### A version history is optional, this will parse the release notes afterward.
      return Request(url= tab_names["revision history"], callback= self.parse_versions,
        meta= {"page_item": item})

    if item["notes_url"] is not None:
      return Request(url= item["notes_url"], callback= self.parse_notes, meta= {"page_item": item})

    ### We are finished, sadly, without much meta-information
    if download_link is None:
      raise Exception("Cannot parse notes and bad download (%s)." % item["binary_name"])
    return Request(url= download_link, callback= self.parse_binary, meta= {"page_item": item})

    pass

  def parse_versions(self, response):
    ### Parse an optional version history
    sel = Selector(response)
    item = response.meta["page_item"]

    previous_versions = []
    versions = sel.css("div#tabContent").css("a.udrline")
    for pversion in versions:
      version_link = "".join(pversion.xpath("@href").extract()).strip()
      version_text = "".join(pversion.xpath(".//text()").extract()).strip()
      version_text = version_text[version_text.find(":")+1:]

      version_id = self._get_update_id(version_link)
      ### Because Dell is stored as an array ...(JSON).
      previous_versions.append([version_text, version_link, version_id])

    item["previous_versions"] = previous_versions

    ### Must now parse notes!
    if item["notes_url"] is not None:
      return Request(url= item["notes_url"], callback= self.parse_notes, meta= {"page_item": item})

    if item["bios_url"] is None:
      raise Exception("Cannot parse notes (after versions) and bad download (%s)." % item["binary_name"])
    return Request(url= item["bios_url"], callback= self.parse_binary, meta= {"page_item": item})

    pass

  def parse_notes(self, response):
    ### Parse a potentially optional release notes section (url).
    sel = Selector(response)
    item = response.meta["page_item"]

    if len(sel.css("div#tabContent").xpath(".//font").css(".heading")) > 0:
      return self.parse_advanced_notes(response)

    ### This content is a textual-dump
    sections = {}
    content = [line.strip() for line in sel.css("div#tabContent").xpath(".//td//text()").extract()]

    active_section = None
    for line in content:
      ### Find a SECTION: Value, or SECTION: (where the value follows on newlines).
      match = re.search(r"([A-Z\(\) ]+):(.*)", line)
      if match is None:
        if active_section is None:
          continue
        ### Add this line to the previously-found section.
        sections[active_section].append(line.strip())
      else:
        match = match.groups()
        if len(match[1]) == 0:
          ### Expect content to follow
          active_section = match[0]
          sections[match[0]] = []
        else:
          active_section = None
          sections[match[0]] = [match[1].strip()]

    #print sections
    section_fields = [
      ("SSM SUPPORTED", "ssm", True),
      ("DESCRIPTION", "desc", False),
      ("PURPOSE", "importance", True),
      ("HARDWARE PRODUCT MODEL(S)", "compatibility", False),
      ("FIXES", "fixes", False)
    ]

    for section_field in section_fields:
      if section_field[0] in sections:
        item[section_field[1]] = sections[section_field[0]]
        if section_field[2] and type(sections[section_field[0]]) == list:
          item[section_field[1]] = item[section_field[1]][0]

    ### Finally, download the BIOS
    if item["bios_url"] is None:

      sp_number = sections["SOFTPAQ NUMBER"][0][:7] if "SOFTPAQ NUMBER" in sections else "0"
      download_link = self._get_download_link(item["binary_name"], sp_number= sp_number)
      if download_link is None:
        raise Exception("Cannot create download (%s), (%s)." % (item["binary_name"], sp_number))
      item["bios_url"] = download_link

    return Request(url= item["bios_url"], callback= self.parse_binary, meta= {"page_item": item})
    pass

  def parse_advanced_notes(self, response):
    sel = Selector(response)

    #content = sel.css("div#tabContent")
    sections = sel.css("div#tabContent").xpath(".//font").css(".heading")
    content = sel.css("div#tabContent").xpath(".//font").css(".body")

    item = response.meta["page_item"]

    sp_section = "SoftPaq"
    sp_number = None
    section_fields = {
      "SSM": "ssm",
      "DESCRIPTION": "desc",
      "PURPOSE": "importance",
      "HARDWARE": "compatibility",
      "FIXES": "fixes"
    }

    for i, section in enumerate(sections):
      section_name = "".join(section.xpath(".//text()").extract())
      section_body = "\n".join([line.strip() for line in content[i].xpath(".//text()").extract() if len(line.strip()) > 0])
      for field, key in section_fields.iteritems():
        if section_name.find(field) == 0:
          if field == "HARDWARE":
            section_body = section_body.split("\n")
          item[key] = section_body
      if section_name.find(sp_section) == 0:
        sp_number = section_body[:7]

      pass

    ### Finally, download the BIOS
    if item["bios_url"] is None:
      download_link = self._get_download_link(item["binary_name"], sp_number= sp_number)
      if download_link is None:
        raise Exception("Cannot create download (%s), (%s)." % (item["binary_name"], sp_number))
      item["bios_url"] = download_link

    return Request(url= item["bios_url"], callback= self.parse_binary, meta= {"page_item": item})
    pass

  def parse_binary(self, response):
    item = response.meta["page_item"]

    print ""
    print json.dumps(dict(item), indent=2)
    print ""

    if item["binary_name"] == "Obtain\u00a0softwar":
      ### This is an odd handling of this error-case, a EULA is required.
      item["binary_name"] = "EULA.html"
    item["binary"] = response.body

    yield item

  #def parse_me_update(self, response):
  #  ### The Intel ME updates have a 'slightly' different format than BIOS updates.
  #  print "Found an ME update", dict(response.meta["result_item"])
  #  pass
