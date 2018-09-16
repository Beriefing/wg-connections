#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import json
import datetime
import MySQLdb
import time
from bs4 import BeautifulSoup
import config
import re

import random

API_KEY = config.config['API_KEY']
API_KEY_PROXY = config.config['API_KEY_PROXY']
DB_USER = config.config['DB_USER']
DB_PW = config.config['DB_PW']
DB_NAME = config.config['DB_NAME']


# Logs all occuring messages and by default writes them to the logfile

def logger(log_message, write_to_file=True):
    message = str(datetime.datetime.now()) + ': ' + str(log_message)
    print (message)
    if write_to_file:
        logfile = open('log.txt', 'a+')
        logfile.write(message + '\n')
        logfile.close()


# Return the basepages

def get_wg_gesucht_websites():
    results = [('Berlin',
               'https://www.wg-gesucht.de/wg-zimmer-in-Berlin.8.0.0.0.html'
               , 'WG')]
    results.append(('Berlin',
                   'https://www.wg-gesucht.de/1-zimmer-wohnungen-in-Berlin.8.1.0.0.html'
                   , 'Flat'))
    results.append(('Berlin',
                   'https://www.wg-gesucht.de/wohnungen-in-Berlin.8.2.0.0.html'
                   , 'Flat'))

    return results


# Returns a working proxy using gimmeproxy.com

def get_proxy(proxy_count, target_datetime):
    params = {}
    params['api_key'] = API_KEY_PROXY
    params['get'] = 'true'
    params['user-agent'] = 'true'
    params['supportsHttps'] = 'true'
    params['protocol'] = 'http'
    params['minSpeed'] = '300'
    params['country'] = 'DE,AT,CH'
    while True:
        proxy_count += 1
        if proxy_count >= 240:  # Check if proxy count is reached
            logger ("Reached proxy limit. Sleeping until "+str(target_datetime))
            while datetime.datetime.now() < target_datetime:  # Wait until next day
                time.sleep(600)
            proxy_count = 0
        json_response = \
            json.loads(get_website('https://gimmeproxy.com/api/getProxy'
                       , params=params))  # Get new proxy via API + API KEY
        proxies = json_response['ip'] + ':' + json_response['port']
        logger(proxies)
        try:
            test_2 = requests.get('https://api.ipify.org/?format=json',
                                  proxies={'https': json_response['ip']
                                  + ':' + json_response['port']})  # Test if proxy is working
            logger(json.loads(test_2.text)['ip'])
            if test_2.status_code == 200:
                logger("good proxy")
                return (proxies, proxy_count)
        except Exception as e:
            logger(e)
            continue


# Retrieves a website using requests lib. This function is used for making all API-related requests that do not require a proxy / anonymity

def get_website(url, params={}, proxies={}):
    retries = 0
    while True:
        try:
            response = requests.get(url, params=params)
            return response.text
        except Exception as e:
            logger(e, True)
            time.sleep(30)
            retries += 1
        if retries > 2:
            return ''


# Retrieves the GPS coords of a given address

def get_coords_from_address(address, city):
    logger(address)
    if len(address) <= 2:  # If address only contains the street and the postcode, append the city (can happen if parses messes up )
        address += city

    address = address[:3]   #Limit address to street+number,postcode,city (make sure, no additional data, e.g. name of district, is appended to query)

    while len(address) >= 2:
        coord_url = \
            'https://api.opencagedata.com/geocode/v1/json?&no_annotations=1&countrycode=DE&q=' \
            + ','.join(address) + '&key=' + API_KEY
        json_response = get_website(coord_url)
        logger(coord_url)
        try:
            result = json.loads(json_response)['results']
            if result and len(result) and result[0]['confidence'] > 1:
                lat = result[0]['geometry']['lat']
                lon = result[0]['geometry']['lng']
                return (lat, lon)
            else:
                del address[-1]
                time.sleep(2)
        except Exception as e:
            logger(e)
            del address[-1]
            time.sleep(2)
    return (0, 0)


# Can be used to remove common address problems ("Nahe" is "close to" in German).

def regulate_output(string):
    string.replace('\n', '')
    string.replace('xx', '')
    string.replace("nahe","").replace ("Nahe","")
    string.replace (str("nähe"),"").replace (str("Nähe"),"")

    return re.sub(' +', ' ', string).strip()


# This function extracts the apartment data (rent,address,wanted gender) from the offer page using BeautifulSoup

def get_data_from_id(ad_id, html, basis_website):
    soup = BeautifulSoup(html, 'html.parser')
    address_html = soup.find_all('a',
                                 {'style': 'line-height: 1.5em;font-weight: normal; color: #555; margin-bottom: 23px;'
                                 })[0]

    street = regulate_output(address_html.text.split('''

''')[0])  # First row contains street name and house number
    city_postcode = \
        regulate_output(address_html.text.split('''

''')[1])  # Second row contains city and postcode
    address = [street] + city_postcode.split()  # This step is necessary to get the output [street number, postcode, city]

    address_html_rent = soup.find_all('td',
            {'class': 'col-xs-6 col-sm-4 print_text_left'})[0]  # Find Rent
    rent = address_html_rent.text.strip()[:-1]

    if 'wohnung' not in basis_website:  # Check if apartment is flatshare (wanted gender relevant) or entire apartment
        address_html_gender = soup.find_all('ul',
                {'class': 'ul-detailed-view-datasheet print_text_left'
                })[1]
        if 'Frau oder Mann' in address_html_gender.text:
            gender = 2
        elif 'Frau' in address_html_gender.text:
            gender = 1
        else:
            gender = 0
    else:
        gender = 2
    return (address, rent, gender)


# This function inserts the data for a given apartment into the database

def insert_sql_entry(
    ad_id,
    lat,
    lon,
    rent,
    gender,
    city,
    type_flat,
    ):
    db = MySQLdb.connect(host='localhost', user=DB_USER, passwd=DB_PW,
                         db=DB_NAME)
    cursor = db.cursor()
    try:
        cursor.execute("""INSERT INTO wgs (id,lat,lon,rent,gender,city,datetime_add,type) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
                       , (
            ad_id,
            lat,
            lon,
            rent,
            gender,
            city,
            datetime.datetime.now(),
            type_flat,
            ))
        db.commit()
        return True
    except Exception as e:
        logger(e, True)
        return False


# Check if a given ad id is already in the DB

def id_in_db(ad_id):
    db = MySQLdb.connect(host='localhost', user=DB_USER, passwd=DB_PW,
                         db=DB_NAME)
    cursor = db.cursor()
    try:
        cursor.execute("""SELECT * from wgs WHERE id=%s""", (ad_id, ))
        result = cursor.fetchall()
        if len(result) > 0:
            return True
        else:
            return False
    except Exception as e:
        logger(e, True)
        return True


# This removes old data (older then 10 days) from the database. Older entries are probably invalid

def remove_old_data():
    db = MySQLdb.connect(host='localhost', user=DB_USER, passwd=DB_PW,
                         db=DB_NAME)
    cursor = db.cursor()
    ten_days_ago = \
        datetime.datetime.combine(datetime.datetime.now().date()
                                  - datetime.timedelta(days=10),
                                  datetime.time(0))
    try:
        cursor.execute("""DELETE FROM wgs WHERE datetime_add=%s """,
                       (ten_days_ago, ))
        db.commit()
        return True
    except Exception as e:
        logger(e, True)
        return False


 # Scroll down (to make link visible)

def scroll(browser, x, y):
    browser.execute_script('window.scrollTo(' + str(x) + ',' + str(y)
                           + ')')
    time.sleep(1)
