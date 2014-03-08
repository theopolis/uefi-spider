
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import FormRequest, Request

from uefispider.items import *

import json

#from scrapy.shell import inspect_response
#inspect_response(response)

class IntelSpider(UefiSpider):
  name = 'IntelSpider'
  allowed_domains = [
    "downloadcenter.intel.com", 
    "downloadmirror.intel.com",
    "search.intel.com",
  ]

  start_urls = [
    "https://downloadcenter.intel.com/Default.aspx?lang=eng",
  ]

  def parse(self, response):
    url = "https://downloadcenter.intel.com/SearchResult.aspx?lang=eng"

    search_form = {
      "search_downloads": ".BIO",
      "ctl00$body$submit_search_downloads": "Search downloads",
      "ctl00$body$searchKeyword": "BIO"
    }

    return [FormRequest(url= url, method= "POST",
      formdata= search_form, callback= self.parse_form)]

  def parse_form(self, response):
    '''Walking 'to' a form is not required, but just incase act like a human.'''

    ### The form will response with HTML, but data is refreshed with an XMLHTTP request.
    url = "https://downloadcenter.intel.com/JSONDataProvider.aspx?DownloadType=BIOS&pg=1&sortDir=descending&Hits=%d&keyword=BIO&lang=eng&refresh=filters&dataType=json&type=GET"

    sel = Selector(response)
    num_results = sel.css("span#num_results")
    if len(num_results) != 1:
      print "Error no results found?"
      return

    ### Example NNNN matching result(s)
    num_results = num_results.css("::text").extract()[0].split(" ")[0]
    try:
      num_results = int(num_results)
    except Exception, e:
      print "Cannot format results count as number? (%s)" % str(e)
      return

    ### Now send an AJAX request for ALL matching items.
    json_data = {
      "DownloadType": "BIOS",
      "pg": "1",
      "sortDir": "descending",
      "Hits": "%d" % num_results,
      "keyword": "\"BIO\"",
      "lang": "eng",
      "refresh": "filters",
      "dataType": "json",
      "type": "GET"
    }

    json_headers = {
      "X-Requested-With": "XMLHttpRequest",
      "Accept": "application/json, text/javascript, */*",
    }

    return [FormRequest(url= url % num_results, method= "POST", headers= json_headers, 
      formdata= json_data, callback= self.parse_json)]

  def parse_json(self, response):
    '''A JSON object of the search results.'''

    download_url = "https://downloadcenter.intel.com%s"

    ### The result response SHOULD be JSON.
    try:
      results = json.loads(response.body)
    except Exception, e:
      print "Cannot load JSON results. (%s)" % str(e)
      return

    items = []
    updates= results["results"]
    for update in updates:
      item = IntelBiosUpdateLinkItem()
      item["item_id"] = update["title"]["downloadid"]
      item["url"] = update["title"]["href"]
      item["name"] = update["title"]["header"]
      item["date"] = update["date"]
      item["version"] = update["version"]
      item["desc"] = update["title"]["description"]
      item["status"] = update["status"]

      yield Request(url= download_url % item["url"], callback= self.parse_download,
        meta= {"attrs": item})

  def parse_download(self, response):
    '''The download page (usually) offers multiple download links, we want just the update.'''

    sel = Selector(response)

    link_notes = None
    link_bios  = None

    links = sel.css('a').xpath('@href').extract()
    for link in links:
      ### Release notes are cool too, though they are in PDF form.
      if link.find("ReleaseNotes") >= 0:
        link_notes = link
      if link.find(".BIO") >= 0:
        link_bios = link

    if link_bios is None:
      return
    
    item = IntelBiosUpdatePageItem()
    link_bios = link_bios[link_bios.find("httpDown=")+len("httpDown="): link_bios.find(".BIO")+len(".BIO")]
    item['bios_url'] = link_bios
    item['notes_url'] = link_notes if link_notes is not None else ""

    ### Supported products is nice too.
    products = []
    products_sel = sel.css('div#prodos')
    if len(products_sel) > 0:
      products_sel = products_sel.xpath(".//table/tr/td/text()").extract()
      for product in products_sel:
        products.append("".join([c for c in product if c not in ['\t', '\n', '\r']]))
    item['products'] = products
    item['attrs'] = dict(response.meta['attrs'])
    item['item_id'] = item['attrs']['item_id']

    #yield item
    yield Request(url= link_bios, callback= self.parse_binary,
      meta= {"item": item})
    pass

  def parse_binary(self, response):
    item = response.meta["item"]
    item["binary"] = response.body

    yield item
