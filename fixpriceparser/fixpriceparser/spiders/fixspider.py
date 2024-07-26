import scrapy
import json
import time
from ..items import FixpriceItem
import os


class FixspiderSpider(scrapy.Spider):
    name = "fixspider"
    categories_urls = json.loads(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'categories.json')).read())
    categories_urls = categories_urls['categories']
    current_category = ''
    current_index = 0
    limit = 99
    api_url = "https://api.fix-price.com/buyer/v1/product/in/"
    page_url = "https://fix-price.com/catalog/"

    def start_requests(self):
        self.current_category = self.categories_urls[0].split('catalog/')[1]
        yield scrapy.Request(
            url=self.api_url + self.current_category + f"?page=1&limit={self.limit}&sort=sold",
            callback=self.parse, method='POST')

    def parse(self, response):
        data = response.json()
        for el in data:
            items = FixpriceItem()
            items['timestamp'] = time.time_ns()
            items['RPC'] = el['id']
            items['url'] = self.page_url + el['url']
            items['title'] = el['title']
            items['marketing_tags'] = el['specialPrice'] if el['specialPrice'] else []
            items['brand'] = el['brand']['title'] if el['brand'] else ''
            items['price_data'] = {
                'current': float(el['specialPrice']['price']) if el['specialPrice'] else float(el['price']),
                'original': float(el['price']),
                'sale_tag': f"Скидка {((float(el['price']) - float(el['specialPrice']['price'])) / float(el['price'])) * 100}%" if
                el['specialPrice'] else ''
            }
            items['stock'] = {
                'in_stock': el['inStock'] > 0,
                'count': el['inStock']
            }
            items['assets'] = {
                'main_image': el['images'][0]['src'],
                'set_images': [x['src'] for x in el['images']],
                "view360": [],
                "video": []
            }
            items['variants'] = el['variantCount']
            yield scrapy.Request(url=self.page_url + el['url'], callback=self.parse_page, meta={'items': items})
        if len(data) == 99:
            url = response.url
            page = int(url.split('page=')[1][0]) + 1
            yield scrapy.Request(
                url=self.api_url + self.current_category + f"?page={page}&limit={self.limit}&sort=sold",
                callback=self.parse, method='POST')
        else:
            self.current_index += 1
            self.current_category = self.categories_urls[self.current_index].split('catalog/')[1]
            yield scrapy.Request(
                url=self.api_url + self.current_category + f"?page=1&limit={self.limit}&sort=sold",
                callback=self.parse, method='POST')

    def parse_page(self, response):
        items = response.meta['items']
        items['section'] = response.xpath("//div[contains(@class, 'breadcrumbs')]/div[contains(@class, 'crumb')]//span[@itemprop='name']/text()").getall()[2:-1]
        items['metadata'] = {
            '__description': response.xpath("//div[@itemscope='itemscope']//div[@class = 'description']/text()").get()
        }
        properties = [scrapy.Selector(text=el) for el in response.xpath("//div[@class='additional-information']//p[@class='property']").getall()]
        for prop in properties:
            items['metadata'].update({
                prop.xpath("//span[@class='title']/text()").get(): prop.xpath("//span[@class='value']/text()").get()
            })
        yield items

