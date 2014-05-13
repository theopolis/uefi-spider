
from uefispider.spiders import UefiSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest
### Need to change useragent
from scrapy.utils.project import get_project_settings

from uefispider.items import *

import json
import re
import copy

def _select_form(index, categories):
    ### Start at Repeater{index} and add each category in the tuple.
    repeater = []
    for category in categories:
        repeater.append("Repeater%d$%s" % (index, category))
        index += 1
    form = {
        "ScriptManager1": "ScriptManager1|%s$LinkButton1" % "$".join(repeater),
        "langNormal": "en",
        "hd_l_series": "Series",
        "hd_l_model": "Model",
        "hd_l_os": "OS",
        "hd_select_type": "1",
        "__EVENTTARGET": "%s$LinkButton1" % "$".join(repeater),
        "__EVENTARGUMENT": "",
        "__ASYNCPOST": "true"
    }
    return form

class AsusSpider(UefiSpider):
    name = 'AsusSpider'
    allowed_domains = [
        "asus.com"
    ]

    product_types = [
        ("ct100", "ct100"), # Laptops
        ("ct101", "ct100"), # Tablets
        ("ct102", "ct100"), # Motherboards
        ("ct103", "ct100"), # Barebones
        ("ct103", "ct101"), # Desktops
        ("ct103", "ct102"), # All-in-Ones
        ("ct104", "ct100"), # Servers
    ]

    start_urls = [
        ### Start at model selector.
        "http://support.asus.com/download/options.aspx?SLanguage=en",
    ]

    select_urls = [
        "http://support.asus.com/Select/ModelSelect.aspx?SLanguage=en&type=1&KeepThis=true",
    ]

    def _get_uas(self):
        ### Edit user agent
        settings = get_project_settings()
        return " ".join([
            settings.get("USER_AGENT"),
            ### The ASP.NET application is checking for async-compatible browsers.
            "Mozilla/5.0 (Windows NT 6.1; WOW64)"
            #"AppleWebKit/537.36 (KHTML, like Gecko)",
            #"Chrome/34.0.1847.116",
            #"Safari/537.36",
        ])
        pass

    def parse(self, response):

        yield Request(url= self.select_urls[0],
            headers= {"User-Agent": self._get_uas()}, 
            #meta= {"cookiejar": "GLOBAL"},
            callback= self.parse_again)
        
    def parse_again(self, response):
        sel = Selector(response)

        hidden_fields = {}
        inputs = sel.xpath("//input")
        for ele in inputs:
            input_type = ele.xpath(".//@type").extract()[0]
            value = ele.xpath(".//@value").extract()[0]
            name = ele.xpath(".//@name").extract()[0]
            if input_type not in ["hidden"]:
                continue
            hidden_fields[name] = value

        for product_type in self.product_types:
            ### Create a POST form and apply a generated ScriptManager
            form_data = _select_form(1, product_type)
            for field in hidden_fields:
                ### Replace static fields with page-generated inputs.
                form_data[field] = hidden_fields[field]
            #print form_data
            yield FormRequest(formdata= form_data, method= "POST",
                headers= {
                    "Content-Type": "application/x-www-form-urlencoded",
                    #"X-MicrosoftAjax": "Delta=true",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": self._get_uas()
                },
                url= self.select_urls[0],
                #meta= {"cookiejar": "GLOBAL"},
                callback= self.parse_series)
            return

    def parse_series(self, response):
        sel = Selector(response)

        from scrapy.shell import inspect_response
        inspect_response(response)