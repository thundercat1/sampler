from lxml import html
from lxml.cssselect import CSSSelector
import requests
import random
import json
import time




class Page:
    def __init__(self, url, description, user_agent, baseurl):
        assert description in ['pdp','homepage','plp'], 'Invalid page type description'
        self.baseurl = baseurl;
        self.url = url
        header = {'User-agent': user_agent}
        page = requests.get(url)
        self.tree = html.fromstring(page.content)
        self.description = description
        self.last_scrape = time.time()
        self.user_agent = user_agent

    def throttle(self, wait_time):
        while (self.last_scrape + wait_time) > time.time():
            #wait a quarter second before checking again
            time.sleep(.25)
        return True

    def create_plps(self, category_limit, min_wait_time):
        plps = set([])
        assert self.description == 'homepage', "Must create plp's beginning with the homepage."
        nav_categories = self.tree.xpath('//nav')
        count = 0
        self.last_scrape = time.time()
        for category in nav_categories[2:]:
            for a,b,link,d in html.iterlinks(category):
                self.throttle(min_wait_time)
                if link[0:4] != 'http' and link not in ('/Store/catalog/shopAllBrands.jsp', '#', '/Store/cart/cart.jsp') and count < category_limit:
                    url = self.url + link
                    print count, 'PLPs loaded so far. Loading PLP from ', url
                    plps.add(Page(url,'plp', self.user_agent, baseurl))
                    self.last_scrape = time.time()
                    count += 1
        return plps

    def random_pdp(self):
        assert self.description == 'plp', "Must select PDP by beginning from a PLP"
        sel = CSSSelector('.qa-product-link')
        items = self.tree.xpath(sel.path)
        if len(items) > 0:
            choice = random.randrange(0,len(items))
            url = baseurl + items[choice].get('href').split('?')[0]
            return Page(url, 'pdp', self.user_agent, self.baseurl)
        else:
            return False

    def prices(self):
        #Returns a dictionary of prices found on the PDP {sku: price, sku2: price2} 


        scripts = self.tree.xpath('//script')

        #Figure out if there is a pricelist for new buybox, and find which script it's in
        scriptIndex = 0
        while (scriptIndex < len(scripts) and html.tostring(scripts[scriptIndex])[47:60] != 'product.sizes'):
            scriptIndex += 1


        try:
            #Try to get prices from price list at the index we found
            try:
                sku_list = html.tostring(scripts[scriptIndex]).split("BC.product.skusCollection = $.parseJSON('")[1]. \
                        split("BC.product.sortedSkusList")[0].strip().split("');")[0];

                sku_list_json = json.loads(sku_list.replace("\\",""))
                pdp_prices = {}
                for key in sku_list_json.keys():
                    pdp_prices[key] = sku_list_json[key]['displayPrice']
                return pdp_prices
            
            except:
                print 'Thought there was a prices list, but couldn not parse it to find prices.'

        except:
            try:
                #try to get prices from unified dropdown
                print 'trying to get prices from unified dropdown'
                unified_prices = self.tree.xpath('//*[@id="unifiedropdown-sku-selector"]/ul/li')
                print unified_prices
                return false

            except:
                print "Could not get prices from ", self.url
                return False

    def store_prices(self, f, prices):
        global PRICES
        #Takes a Page object and filename
        #Writes to the file 
        assert self.description == 'pdp', "Need to get price from a PDP only"
        if prices:
            for sku in prices.keys():
                if sku not in PRICES:
                    price = prices[sku]
                    PRICES[sku] = {'price': price, 'url': self.url}
                    f.write(sku + ',' + price[1:] + ',' + self.url + '\n')



if __name__ == '__main__':

    def throttle(wait_at_least):
        global last_scrape
        while (last_scrape + wait_at_least) > time.time():
            pass
        else:
            last_scrape = time.time()
    baseurl = open('baseurl.txt', 'r').read().strip();
    user_agent = 'a'
    outfilename = 'price_scrape.csv'

    PLPs = set([])
    PRICES = {}

    category_limit = 10
    price_goal = 500
    wait_at_least = 3
    max_failed_prices = 100
    
    last_scrape = time.time()
    failed_pdps = 0

    outfile = open(outfilename, 'w')
    outfile.write('sku,price,url\n')
    
    homepage = Page(baseurl, 'homepage', user_agent, baseurl)
    PLPs = homepage.create_plps(category_limit, wait_at_least)

    while (len(PRICES) < price_goal) and (failed_pdps < max_failed_prices):
        throttle(wait_at_least)
        plp = random.choice(tuple(PLPs))
        selected_pdp = plp.random_pdp()
        if selected_pdp:
            prices = selected_pdp.prices()
            if prices:
                selected_pdp.store_prices(outfile, prices)
                print len(PRICES), 'out of goal', price_goal, 'prices found'
            else:
                failed_pdps += 1
                print failed_pdps, 'failed'
