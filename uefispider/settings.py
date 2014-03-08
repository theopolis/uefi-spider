# Scrapy settings for uefispider project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'uefispider'

SPIDER_MODULES = ['uefispider.spiders']
NEWSPIDER_MODULE = 'uefispider.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'uefispider (+https://github.com/theopolis/uefi-spider)'

ITEM_PIPELINES = {
  'uefispider.pipelines.UefispiderPipeline': 1
}