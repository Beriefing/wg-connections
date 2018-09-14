#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import json
import datetime
import MySQLdb
import time
from geojson import Feature, Point, FeatureCollection
import config
import math

DB_USER = config.config['DB_USER']
DB_PW = config.config['DB_PW']
DB_NAME = config.config['DB_NAME']
API_KEY = config.config['API_KEY']

gender_dict = {0: 'M', 1: 'W', 2: 'MW'}
transport_dict = {
    'Public Transport': 'pt',
    'Car': 'car',
    'Bike': 'bike',
    'Walk': 'foot',
    }

# Logs all occuring messages and by default writes them to the logfile

def logger(log_message, write_to_file=True):
    message = str(datetime.datetime.now()) + ': ' + str(log_message)
    print(message)
    if write_to_file:
        logfile = open('log.txt', 'a+')
        logfile.write(message + '\n')
        logfile.close()


# Retrieves a website using requests lib.

def get_website(url, params={}, proxies={}):
    retries = 0
    while True:
        try:
            response = requests.get(url, params=params)
            return response.text
        except Exception as e:
            logger(e)
            time.sleep(30)
            retries += 1
        if retries > 2:
            return ''


# Retrieves the GPS coords of a given address

def get_coords_from_address(address, city):
    logger("ADDRESS: "+str(address))
    if len(address) <= 2:  # If address only contains the street and the postcode, append the city (can happen if parses messes up )
        address += city

    address = address[:3]        #Limit address to street+number,postcode,city (make sure, no additional data( e.g. name of district, is appended to query)

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

#Retrieves isochrones GEOJSON from isochrones server
def get_isochrones(
    start_coords,
    vehicle,
    buckets,
    time_limit,
    ):
    vehicle = transport_dict[vehicle]

    params = (('point', ','.join(str(x) for x in start_coords)), )
    params += (('vehicle', vehicle), )
    params += (('buckets', buckets), )
    params += (('time_limit', time_limit), )

    url = 'http://localhost:8991/isochrone'

    return get_website(url, params)


#For each point, retrieve the travel time to the POI from the specific routing server
# coords = (latitude,longitude)

def get_commute_time(start_coords, finish_coords, vehicle):
    vehicle = transport_dict[vehicle]

    params = (('point', ','.join(str(x) for x in start_coords)), )
    params += (('point', ','.join(str(x) for x in finish_coords)), )
    params += (('vehicle', vehicle), )
    params += (('instructions', 'false'), )
    params += (('weighting', 'fastest'), )

    if vehicle == 'pt':
        url = 'http://localhost:8993/route'
        params += (('pt.profile', 'false'), )
        params += (('pt.ignore_transfers', 'true'), )
        params += (('pt.limit_solutions', '1'), )
        params += (('pt.max_walk_distance_per_leg', '1000'), )
        params += (('pt.earliest_departure_time',
                   '2018-11-21T06:00:00.000Z'), )
        params += (('pt.arrive_by', 'false'), )
    else:
        url = 'http://localhost:8989/route'

    json_response = get_website(url, params)

    try:
        paths = json.loads(json_response)['paths']
        duration = -1
        if paths and len(paths):
            duration = paths[0]['time']
            if vehicle == 'car':
                duration = duration * 1.5   #This factor is introduced to make the car travel times during rush hour more realistic
        return duration / (60 * 1000)
    except Exception as e:
        logger(e)
        return -1


#This function creates the corresponding GEOJSON object for a given city and the chosen transport/coords tuple (e.g. "car",("52.1212","8.1212"))
#Note that this function uses the parameters idx and nr_shown to return the correct apartments without duplicates

def create_dist_geojson(
    coords_transport_tuples,
    city,
    idx,
    nr_shown,
    ):
    features = []
    if idx == 0 and nr_shown == 0:
        for coords_transport in coords_transport_tuples:
            features.append(Feature(geometry=Point(coords_transport[:2][:
                            :-1]), properties={'poi': 'true',
                            'duration_0': 0}))

    db = MySQLdb.connect(host='localhost', user=DB_USER, passwd=DB_PW,
                         db=DB_NAME)
    sql_city_entries = get_sql_entries(db, city, nr_shown)

    for entry in sql_city_entries[idx * 5:(idx + 1) * 5]:
        coords_start = entry[1:3]
        wg_point = Feature(geometry=Point(coords_start[::-1]),
                           properties={'poi': 'false'})
        wg_point.properties['link'] = 'https://www.wg-gesucht.de/' \
            + str(entry[0]) + '.html'
        wg_point.properties['rent'] = entry[3]
        wg_point.properties['gender'] = gender_dict[entry[4]]
        wg_point.properties['type'] = entry[5]
        for (idx, coords_transport) in \
            enumerate(coords_transport_tuples):
            commute_time = get_commute_time(coords_start,
                    coords_transport[:2], coords_transport[2])
            wg_point.properties['duration_' + str(idx)] = \
                math.ceil(commute_time)
        features.append(wg_point)

    feature_collection = FeatureCollection(features)

    return feature_collection

#Retrieves entries for a given city.
#Note that nr_shown is the number of the currently displayed houses.

def get_sql_entries(db, city, nr_shown):
    db = MySQLdb.connect(host='localhost', user=DB_USER, passwd=DB_PW,
                         db=DB_NAME)
    cursor = db.cursor()
    cursor.execute("""SELECT id,lat,lon,rent,gender,type FROM wgs WHERE city=%s ORDER BY datetime_add DESC LIMIT %s,50"""
                   , (city, nr_shown))
    result = cursor.fetchall()
    db.close()
    return result
