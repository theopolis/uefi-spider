UEFI Spider
===========
The UEFI Spider is a set of HIGHLY specific scripts containing spidering logic for 
ISV/OEMs providing downloadable UEFI firmware updates. Each spider will attempt to document (in JSON) and download every identified UEFI firmware update.

**WARNING:** Using this tool is dangerous, upon running each spider you will have downloaded well over 50G of firmware updates. This is highly taxing on both your bandwidth and the services hosting the updates. Please read the EULA for each site before spidering. This code is provided for reference only; this project and its authors do not encourage using the spiders. 

Installation
------------
**Requirements**
::

  $ apt-get install libxml2-dev libxslt1-dev python-dev
  $ pip install scrapy

Usage
-----
::

  $ scrapy crawl -a dump=/path/to/spider/output DellSpider

**Supported Vendors**

- ASRock
- Dell
- Gigabyte
- Intel
- Lenovo
- HP
- MSI
- VMware

