# wg-connections
Search flats and flatshares by commuting distance (currently only in Berlin).

## scraper  
The scraper uses Selenium, BeautifulSoup and a rotating-proxy service to scrape data from a certain big German flatsharing website. Currently only data for Berlin is scraped.

## server
The server is based on Flask and uses a Leaflet map to draw the geojson elements returned from a running GraphHopper instance.

## Routing  
There need to be a couple of running (selfhosted) GraphHopper instances with map and GTFS data from Berlin. The setup is as easy as shown in the examples on their [project page](https://github.com/graphhopper/graphhopper).  
Graphhopper Instances:
1. Public Transit (very RAM-intensive), Port: 8993
2. Car, Bike, Walk share one instance, Port: 8989
3. Isochrones (for Car, Bike + Walk), Port: 8991


