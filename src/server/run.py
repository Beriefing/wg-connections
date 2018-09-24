#!/usr/bin/python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, session
from server_helper import *
import config
app = Flask(__name__)
app.config['SECRET_KEY'] = config.config['APP_SECRET']


@app.route('/')
def index():
    client_ip = request.access_route[0]
    logger ("HOME Client IP: "+str(client_ip))
    return render_template('index.html')

@app.route('/about')
def about():
    client_ip = request.access_route[0]
    logger ("ABOUT Client IP: "+str(client_ip))
    return render_template('about.html')


@app.route('/update_poi',methods=['POST'])
def update():

    (address, city) = ([request.json['address'], request.json['zip']],
                       request.json['city'])
    session['city'] = city
    (lat, lon) = get_coords_from_address(address, city)

    if lat == 0 and lon == 0:
        logger("Error")
        return jsonify({"poi":"not_found"})
    else:
        session['lat'] = lat
        session['lon'] = lon
        return jsonify({"poi":"found"})

# Returns GEOJSON response for requested address and vehicle
# Since we don't want to wait until all flats are processed there is a numbering scheme used.

@app.route('/wgs.json', methods=['POST'])
def wgs():

    idx = request.json['idx']   #The entire number of 50 needed flats is split up into parts of 5 flats at a time with the index ranging from 0 to 9

    nr_shown = max(int(request.json['nr_shown']) - 1, 0)  # This is the current number of shown flats. The POI is subtracted from the total number

    # To avoid duplicate geocoding API calls, we store the GPS coords as a session cookie


    lat = session['lat']
    lon = session['lon']
    city = session['city']



    return jsonify(create_dist_geojson([(lat, lon,
                   request.json['transport'])], city, idx, nr_shown))


# Returns the isochrones GEOJSON response for requested address and vehicle

@app.route('/isochrones.json', methods=['POST'])
def isochrones():
    (address, city, vehicle) = ([request.json['address'],
                                request.json['zip']],
                                request.json['city'],
                                request.json['transport'])

    lat = session.get("lat",-1)
    lon = session.get("lon",-1)
    if lat == -1 and lon == -1:
        (lat, lon) = get_coords_from_address(address, city)
        if lat == 0 and lon == 0:
            logger('Error')

    # Divide times into three buckets. Since the given car travel times are approx 1.5 times faster than in reality, we have different time limits

    buckets = 3
    if vehicle == 'Car':
        time_limit = 2400
    else:
        time_limit = 3600

    return jsonify(get_isochrones((lat, lon), vehicle, buckets,
                   time_limit))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
