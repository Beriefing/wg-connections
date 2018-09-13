# wg-connections
Search flats and flatshares by commuting distance (currently only in Berlin).

## scraper  
The scraper uses Selenium, BeautifulSoup and a rotating-proxy service to scrape data from a certain big German flatsharing website. Currently only data for Berlin is scraped.

## server
The server is based on Flask and uses a Leaflet map to draw the geojson elements returned from a running GraphHopper instance.

## GraphHopper  
There need to be a couple of running (selfhosted) GraphHopper instances with map and GTFS data from Berlin.
1. Public Transit (very RAM-intensive)
2. Car, Bike, Walk share one instance
3. Isochrones (for Nr. 2)
