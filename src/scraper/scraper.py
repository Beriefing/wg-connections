#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime
import time
import MySQLdb
import random
import config
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from scraper_helper import *
from pyvirtualdisplay import Display

display = Display(visible=0, size=(1280, 800))
display.start()


# Retrieve all subpages to scrape, respective city and apartment type

wg_gesucht_websites = get_wg_gesucht_websites()
logger(wg_gesucht_websites)

i = 0
proxy_count = 0  # Counts the number of API calls to gimmeproxy (Max. 240 per day)
time_start = 0  # Makes sure, the first abs(time_stop - time_start) is bigger than 300

while True:
    city = wg_gesucht_websites[i][0]
    website = wg_gesucht_websites[i][1]
    type_flat = wg_gesucht_websites[i][2]

# This resets the proxy counter once a new day has begun

    target_datetime = \
        datetime.datetime.combine(datetime.datetime.now().date()
                                  + datetime.timedelta(days=1),
                                  datetime.time(0))
    if datetime.datetime.now() > target_datetime:
        proxy_count = 0
        target_datetime = \
            datetime.datetime.combine(datetime.datetime.now().date()
                + datetime.timedelta(days=1), datetime.time(0))
        remove_old_data()

# Less activity during the night

    if datetime.datetime.now().time() < datetime.time(8, 0, 0, 0):
        time.sleep(600)

    time_stop = time.time()

    if abs(time_stop - time_start) < 300:
        time.sleep(300 - abs(time_stop - time_start))

# Get new proxy. The called function also takes care of the maximum number of allowed proxy requests

    (proxy, new_count) = get_proxy(proxy_count, target_datetime)

    time_start = time.time()
    proxy_count = new_count

    logger('Proxy Number: ' + str(proxy_count))
    logger('City: ' + city)
    logger('Base Website: ' + website)
    logger('Type of Apartment: ' + type_flat)

# Create selenium chromedriver with proxyserver

    options = webdriver.ChromeOptions()
    options.add_argument('--proxy-server=%s' % proxy)
    browser = webdriver.Chrome(chrome_options=options)
    visited = {}

    try:
        browser.get(website)
        j = 0

       # Retrieve all possible links to offers from base website

        offer_list_items = \
            browser.find_elements_by_class_name('offer_list_item')
        logger('OFFER LIST ITEMS: ' + str(len(offer_list_items)))
        while j < len(offer_list_items):
            scroll(browser, 0, 950 + random.randint(16, 25) * j)  # Scroll down randomly (to make link visible)
            ad_id = int(offer_list_items[j].get_attribute('adid'
                        ).split('.')[1])  # Get Offer ID
            logger(ad_id)
            if not id_in_db(ad_id):  # Check if ID is already in DB
                offer_list_items[j].click()
                scroll(browser, 0, 600 + random.randint(-20, 30))  # Scroll randomly again (to make rent and address visible)
                (address, rent, gender) = get_data_from_id(ad_id,
                        html=browser.page_source, basis_website=website)  # Retrieve relevant data from offer page
                if gender == -1 or rent == 'n.a.':  # Check if scraping was successful
                    logger('Fail')
                    i = (i + 2) % 3  # If no success, repeat with same basepage
                    break
                (lat, lon) = get_coords_from_address(address, city)  # Get GPS coords from geocoding service
                if lat != 0 or lon != 0:
                    insert_sql_entry(  # If GPS coords found, insert all data into DB
                        ad_id,
                        lat,
                        lon,
                        rent,
                        gender,
                        city,
                        type_flat,
                        )
                else:
                    logger('FAIL')
                logger((
                    ad_id,
                    lat,
                    lon,
                    rent,
                    gender,
                    address,
                    ))
                browser.back()  # Go back to basepage
                offer_list_items = \
                    browser.find_elements_by_class_name('offer_list_item'
                        )  # Search again (since previous elements are not valid anymore.
                time.sleep(1)  # If new offers have been added to basepage, they will be added the next time)
            j = j + 1
        i = (i + 1) % 3
        browser.close()  # Close browser since new proxy reqeuires new browsing sessions
    except Exception as  e:
        logger(e)
        logger('EXCEPTION')
        browser.close()
        continue
