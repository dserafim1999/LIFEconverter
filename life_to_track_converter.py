import requests, random, os, polyline, argparse, json
from urllib.parse import urlencode

from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from os.path import expanduser, isfile, join
from os import rename

from utils.bounds import EARTH_RADIUS, bounding_locations, bounds_intersection, coords_obj, is_point_in_bounds
from life.life import Life
from utils.utils import update_dict
from utils.default_config import CONFIG

parser = argparse.ArgumentParser(description='')
parser.add_argument('--config', '-c', dest='config', metavar='c', type=str,
        help='configuration file')
parser.add_argument('--google', '-g', dest='use_google_maps_api', metavar='g', type=bool,
        help='use google maps api')
args = parser.parse_args()

def indentation(n):
    return ''.join('\t' for i in range(n))

FAIL_COLOR = '\033[91m'
END_COLOR = '\033[0m'

class LIFEToTrackConverter(object):
    """ 

    """

    def __init__(self, config_file, use_google_maps_api=False):
        self.config = dict(CONFIG)
        if config_file and isfile(expanduser(config_file)):
            with open(expanduser(config_file), 'r') as config_file:
                config = json.loads(config_file.read())
                update_dict(self.config, config)

        self.get_bounds()
        
        self.google_maps_api = use_google_maps_api
        self.set_api()

        for life_file in os.listdir(self.config['input_path']):
            self.life = Life()
            self.life.from_file(os.path.join(self.config['input_path'], life_file))
            self.days = self.life.days
            self.routes = {}
            self.locations = {}

            print(f"Processing {life_file}...")
            self.get_locations_max_distance()
            self.calculate_location_coords()
            self.LIFE_to_gpx()

            life_path = join(expanduser(self.config['input_path']), life_file)
            output_path = join(expanduser(self.config['output_path']), life_file)
            rename(life_path, output_path)

    def get_locations_max_distance(self):
        """ Creates an object that calculates the max distance between locations based on the average travel time between 
        them in a life file and a maximum average speed set in the configuration file
        """

        res = {}
        
        for day in self.days:
            for i in range(1, len(day.spans)):
                prev_span = day.spans[i - 1]
                span = day.spans[i]

                if (prev_span.multiplace() or span.place == prev_span.place or span.place == '' or prev_span.place == ''):
                    continue
                
                if (span.multiplace()):
                    start = span.place[0]
                    end = span.place[1]

                    start_time = span.start_utc()
                    end_time = span.end_utc()

                else: 
                    start = prev_span.place
                    end = span.place
                    
                    start_time = prev_span.end_utc()
                    end_time = span.start_utc()
                
                if (start_time == end_time):
                    continue

                start_datetime = datetime.strptime(start_time,'%Y-%m-%dT%H:%M:%SZ')
                end_datetime = datetime.strptime(end_time,'%Y-%m-%dT%H:%M:%SZ')
                total_time = abs(end_datetime - start_datetime).total_seconds() / 3600 # in hours

                # saves total time bewteen start and end in an entry that translates the route start -> end 
                if start in res:
                    if end in res[start]:
                        res[start][end]['total_time'] += total_time
                        res[start][end]['num'] += 1
                    else:
                        res[start][end] = {'total_time': total_time, 'num': 1}
                else: 
                    res[start] = {end: {'total_time': total_time, 'num': 1 }}
                    self.locations[start] = None

                # saves total time bewteen start and end in an entry that translates the route end -> start
                if end in res:
                    if start in res[end]:
                        res[end][start]['total_time'] += total_time
                        res[end][start]['num'] += 1
                    else:
                        res[end][start] = {'total_time': total_time, 'num': 1}
                else: 
                    res[end] = {start: {'total_time': total_time, 'num': 1 }}
                    self.locations[end] = None

        for start in res:
            for end in res[start]:
                res[start][end]['avg_time'] = (res[start][end]['total_time'] / res[start][end]['num']) # calculates the avg time between start and end
                res[start][end]['max_distance'] = self.config['avg_speed'] * res[start][end]['avg_time'] # calculates the max distance based on the max avg seed and avg time
                res[start][end].pop('total_time')
                res[start][end].pop('num')

        self.distances = res

    def calculate_location_coords(self):
        """ Gradually reduces the bounding boxes of possible point locations throughout several iterations, 
        finishing with the generation of coordinates in the final bounding box for each location. If coordinates are explicitly defined in 
        the LIFE file, these are used.
        """

        candidate_bounds = {}
        locations = temp_locations = list(self.distances.keys())

        # sets initial bounds (defined in config file) and moves locations with known coords to the top of the list to be sorted first
        for location in temp_locations:
            if location in self.life.coordinates:
                locations.insert(0, locations.pop(locations.index(location)))
                coords = self.life.coordinates[location]
                centre = coords_obj(coords[0], coords[1])
                candidate_bounds[location] = bounding_locations(centre, 0.1) #set bounds to 0.1km radius from known coordinates
            else:
                candidate_bounds[location] = self.bounds 
            self.locations[location] = None

        for i in range(0, self.config['bounds_iterations']):
            for origin in locations:
                if origin in self.life.coordinates: # if coordinates are explicitly defined in LIFE file, set them
                    coords = self.life.coordinates[origin]
                    self.locations[origin] = coords_obj(coords[0], coords[1]) 
                elif self.locations[origin] == None or is_point_in_bounds(self.locations[origin], candidate_bounds[origin]): #if point isn't set yet or candidate point no longer in candidate bounds 
                    self.locations[origin] = self.random_point_in_bounds(candidate_bounds[origin])
                
                for destination in self.distances[origin]:
                    possible_radius = bounding_locations(self.locations[origin], self.distances[origin][destination]['max_distance'])
                    candidate_bounds[destination] = bounds_intersection(candidate_bounds[destination], possible_radius)   

        self.update_LIFE_locations()
        
    def set_api(self):
        """ Selects what API to use based on if explicitly set and/or based on what keys were set in the configuration file
        """

        # if no API key is set, quit program
        if len(self.config['google_maps_api_key']) == 0 and len(self.config['tom_tom_api_key']) == 0:
            print(f"{FAIL_COLOR}No API set to generate routes.\nPlease set a Google Maps or TomTom API key in your configuration JSON file.{END_COLOR}")
            quit()

        # checks if Google API key is set, uses Tom Tom API key if not
        if self.google_maps_api:
            if len(self.config['google_maps_api_key']) > 0:
                self.api_key = self.config['google_maps_api_key']
                print("Using Google Maps Directions API to generate routes.")
            elif len(self.config['tom_tom_api_key']) > 0:
                self.api_key = self.config['tom_tom_api_key']
                self.google_maps_api = False
                print("Using Tom Tom Routing API to generate routes.")

        # checks if Tom Tom API key is set, uses Google API key if not
        else:
            if len(self.config['tom_tom_api_key']) > 0:
                self.api_key = self.config['tom_tom_api_key']
                self.google_maps_api = False
                print("Using Tom Tom Routing API to generate routes.")
            elif len(self.config['google_maps_api_key']) > 0:
                self.api_key = self.config['google_maps_api_key']
                print("Using Google Maps Directions API to generate routes.")

    def get_bounds(self):
        """ Stores bounds for random coordinates generation defined in the config file

            :obj:`list` of :obj:`dict` : Contains the two points that define an upper and lower corner of the bounds 
        """
        
        point1 = coords_obj(self.config['bounds']['point1']['lat'], self.config['bounds']['point1']['lng'])
        point2 = coords_obj(self.config['bounds']['point2']['lat'], self.config['bounds']['point2']['lng'])

        self.bounds = (point1, point2)

    def update_LIFE_locations(self):
        """ Updates locations for cases such as subplaces and name changes in the LIFE file 
        """ 
    
        for location in self.life.all_places():
            if (location in self.life.superplaces.keys()):
                self.locations[location] = self.locations[self.life.superplaces[location]] # if subplace, set the coordinates of its superplace
            
            if (location in self.life.nameswaps or location in self.life.locationswaps):
                self.locations[self.life.nameswaps[location][0]] = self.locations[location] # if place changed name or if something new in same location, copies coords from original to new
          
    def distance(self, coords1, coords2): 
        """ Calculates distance, in km, of two coordinates defined by latitude and longitude
        taken from https://www.geeksforgeeks.org/program-distance-two-points-earth/#:~:text=For%20this%20divide%20the%20values,is%20the%20radius%20of%20Earth.

        Args:
            coords1 (:obj:`dict`): Coordinates of the first point
            coords2 (:obj:`dict`): Coordinates of the second point
        Returns:
            float: distance between both points
        """
        lat1 = radians(coords1['lat'])
        lng1 = radians(coords1['lng'])
        lat2 = radians(coords2['lat'])
        lng2 = radians(coords2['lng'])
        
        # Haversine formula
        dlng = lng2 - lng1 
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
    
        c = 2 * asin(sqrt(a))
        
        return abs(c * EARTH_RADIUS)

    def random_point_in_bounds(self, bounds):
        """ Generates a random latitude/longitude pair inside specified bounds
        Returns:
            :obj:`dict`: Coordinates defined by a dictionary with 'lat' and 'lng' keys
        """

        lat = random.uniform(min(bounds[0]['lat'], bounds[1]['lat']), max(bounds[0]['lat'], bounds[1]['lat']))
        lng = random.uniform(min(bounds[0]['lng'], bounds[1]['lng']), max(bounds[0]['lng'], bounds[1]['lng']))

        return coords_obj(lat, lng)

    def calculate_speed(self, distance, time):
        """ Calculates the speed given the distance and time
        Args: 
            distance (float): Distance of route
            time (int): Duration of route 
        Returns:
            float: resulting speed 
        """
        if time == 0: 
            return 0 
        else: 
            return distance / time

    def parse_duration_in_seconds(self, response):
        """ Parses duration from http request response into seconds
        Args:
            response (:obj:`dict`:): http response for the routing request
        Returns:
            int: duration in seconds
        """

        if self.google_maps_api:
            string = response['routes'][0]['legs'][0]['distance']['text']
            words = string.split(" ")
            hours = mins = 0

            if "hour" in words[1]:
                hours = int(words[0])
                if len(words) == 4:
                    mins = int(words[2])
            elif "min" in words[1]:
                mins = int(words[0])
            result = 3600 * hours + 60 * mins
        else:
            result = response['routes'][0]['summary']['travelTimeInSeconds']
        
        return result

    def parse_distance_in_metres(self, response):
        """ Parses distance from http request response into metres
        Args:
            response (:obj:`dict`:): http response for the routing request
        Returns:
            float: distance in metres 
        """
        result = 0

        if self.google_maps_api:
            string = response['routes'][0]['legs'][0]['distance']['text']

            words = string.split(" ")
            kms = 0

            if "km" in words[1]:
                kms = float(words[0])
                
            result = kms * 1000
        else:
            result = response['routes'][0]['summary']['lengthInMeters']

        return result
    
    def parse_coords(self, coords):
        """ Parses coordinates into a formatted string for an http request 
        Args:
            coords (:obj:`tuple`:): coordinate pair containing latitude and longitude
        Returns:
            string: formatted string to be set as an http request parameter => "lat, lng"
        """
        return f"{coords['lat']},{coords['lng']}"

    def parse_points(self, response):
        """ Parses points into a list of coordinate pairs
        Args:
            response (:obj:`tuple`:): http response for the routing request 
        Returns:
            :obj:`list`: of :obj:`tuple`: list of point coordinate pairs 
        """
        if self.google_maps_api:
            polyline_points = response['routes'][0]['overview_polyline']['points'] 
            return polyline.decode(polyline_points)
        else:
            return [(point['latitude'], point['longitude']) for point in response['routes'][0]['legs'][0]['points']]

    def get_route(self, start, end, start_time, end_time, data_type = 'json'):
        """ Calculates route for a span, from "start" to "end", that starts at "start_time" and ends at "end_time"
        Args:
            start (string): coordinates (or location name) of the route's origin
            end (string): coordinates (or location name) of the route's destination
            start_time (string): formatted string representing the route's start time in the `%Y-%m-%dT%H:%M:%SZ` format
            end_time (string): formatted string representing the route's end time in the `%Y-%m-%dT%H:%M:%SZ` format
            data_type (string): string representing data type to be returned by the api
        Returns:
            :obj:`list` of :obj:`dict`: list containing the latitude, longitude and timestamps of the points that describe the route
        """

        start_datetime = datetime.strptime(start_time,'%Y-%m-%dT%H:%M:%SZ')
        end_datetime = datetime.strptime(end_time,'%Y-%m-%dT%H:%M:%SZ')
        total_time = (end_datetime - start_datetime).total_seconds()

        timestamp = start_datetime

        # check if the route has been calculated previously, and update timestamps if so
        if (start in self.routes and end in self.routes[start]): 
            total_distance = self.routes[start]['total_distance']
            points = self.routes[start][end]
            avg_speed = self.calculate_speed(total_distance, total_time)

            for i in range(0, len(points) - 1):
                point = points[i]
                next_point = points[i + 1]
                
                point['time'] = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
                time_btwn_points = self.calculate_time_btwn_points(point, next_point, avg_speed)
                timestamp += timedelta(seconds=time_btwn_points)

            points[len(points) - 1]['time'] = end_time # sets end time to last point

            return points
        
        # http request setup
        if self.google_maps_api:
            endpoint = f"https://maps.googleapis.com/maps/api/directions/{data_type}"
            params = {"origin": start, "destination": end, "key":  self.config['google_maps_api_key']}
        else:
            endpoint = f"https://api.tomtom.com/routing/1/calculateRoute/{start}:{end}/{data_type}"
            params = {"routeRepresentation": "polyline", "key":  self.config['tom_tom_api_key']} 

        url_params = urlencode(params)
        url = f"{endpoint}?{url_params}"

        # requests directions between 2 locations from the either the Tom Tom Routing or Google Maps Directions API 
        r = requests.get(url)

        result = {}
        if r.status_code not in range(200, 299):
            return {}

        try:
            result = r.json()
            if 'OK' not in result['status'] or 'detailedError' in result: # checks if request was successful 
                return {} 
        except:
            pass

        raw_points = self.parse_points(result) # points that describe the route
        total_distance = self.parse_distance_in_metres(result)
        avg_speed = self.calculate_speed(total_distance, total_time)
        
        points = []

        for i in range(0, len(raw_points) - 1):
            point = coords_obj(raw_points[i][0], raw_points[i][1])
            next_point = coords_obj(raw_points[i + 1][0], raw_points[i + 1][1])

            time_btwn_points = self.calculate_time_btwn_points(point, next_point, avg_speed) # calculates step between points (just an average)
            
            point['time'] = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
            points.append(point)
            timestamp += timedelta(seconds=time_btwn_points)

        points.append(coords_obj(raw_points[len(raw_points) - 1][0], raw_points[len(raw_points) - 1][1], end_time)) # sets coordinates and end time for last point

        self.routes[start] = {end: points, 'total_distance': total_distance} # saves calculated route for future reference 

        return points

    def calculate_time_btwn_points(self, coords1, coords2, speed):
        """ calculates the time, in seconds, between 2 points given a certain speed (in m/s)
        Args:
            coords1 (:obj:`dict`:): coordinates for 1st point 
            coords2 (:obj:`dict`:): coordinates for 2nd point
            speed (float): speed used in the route
        Return:
            float: time between both points give the speed 
        """

        length = self.distance(coords1, coords2) * 1000
        
        return (length / speed) 

    def get_segments(self, day):
        """ Calculates routes for all spans in a LIFE day. Connects two consecutive spans with a route that starts at the span location's 
        final timestamp and ends at the second  span location's start timestamp.
        Args:
            day (:obj:`life.Day`): life.Day object that contains information about the date and the spans of a day 
        Returns:
            :obj:`list` of :obj:`list` of :obj:`dict`: list that contains a list of the points that define the selected day's routes 
        """ 

        res = []
        
        for i in range(1, len(day.spans)):
            prev_span = day.spans[i - 1]
            span = day.spans[i]

            if (prev_span.multiplace() or span.place == prev_span.place or span.place == '' or prev_span.place == ''):
                continue
            
            # if a route is specified in a span, we calculate it using those locations
            if (span.multiplace()):
                start_coords = self.parse_coords(self.locations[span.place[0]])
                end_coords = self.parse_coords(self.locations[span.place[1]])

                start_time = span.start_utc()
                end_time = span.end_utc()

            # if not, we use the previous span to get the start time and location
            else: 
                start_coords = self.parse_coords(self.locations[prev_span.place])
                end_coords = self.parse_coords(self.locations[span.place])
                
                start_time = prev_span.end_utc()
                end_time = span.start_utc()
            
            if (start_time == end_time):
                continue

            route = self.get_route(start_coords, end_coords, start_time, end_time)
            
            res.append(route)
        
        return res

    def point_gpx(self, point):
        """ Parses a point into an xml tag for the gpx file that defines the track 
        Args:
            point (:obj:`dict`): route point defined by latitude (lat), longitude (lng) and timestamp (time)
        Returns:
            string: xml tag <trkpt> that defines a point in the gpx format
        """
        return ''.join([
            indentation(3),
            '<trkpt lat="' + str(point['lat']) + '" lon="' + str(point['lng']) + '">\n',
            indentation(4),
            '<time>' + str(point['time']) + '</time>\n',
            indentation(3),
            '</trkpt>'
        ]) + '\n'

    def segment_gpx(self, segment):
        """ Parses a segment of a route into an xml tag for the gpx file that defines the track 
        Args:
            segment (:obj:`list` of :obj:`dict`): list of points that define a segment of the route
        Returns:
            string: xml tag <trkseg> that defines a segment in the gpx format
        """

        if (len(segment) == 0):
            return ''

        points = ''.join([self.point_gpx(point) for point in segment])
        
        return ''.join([
            indentation(2) + '<trkseg>\n',
            points,
            indentation(2) + '</trkseg>\n',
        ]) + '\n'


    def to_gpx(self, day):
        """ Parses a route into an xml representation for the gpx file that defines the track 
        Args:
            day (:obj:`life.Day`): life.Day object that contains information about the date and the spans of a day 
        Returns:
            string: xml that defines the route in the gpx format
        """

        all_segments = self.get_segments(day)

        if (len(all_segments) == 0):
            return ''

        segments = ''.join([self.segment_gpx(segment) for segment in all_segments])
        
        return ''.join([
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            f'<!-- {day.date} -->\n'
            '<gpx xmlns="http://www.topografix.com/GPX/1/1">\n',
            indentation(1) + '<trk>\n', 
            segments,  
            indentation(1) + '</trk>\n',
            '</gpx>\n'
        ])
    
    def LIFE_to_gpx(self):
        """ Converts a file in the LIFE format into a file in the .gpx format describing a possible set of routes taken for each day
        """
        for day in self.days:
            # Checks if day contains more than one location (in other words, contains at least one route)
            if len(day.all_places()) > 1:
                self.generate_gpx_file(day)

    def generate_gpx_file(self, day):
        """ Creates a file in the gpx format that defines a day
        Args:
            day (:obj:`life.Day`): life.Day object that contains information about the date and the spans of a day 
        """

        with open(f"{self.config['output_path']}\\{day.date}.gpx", "w+") as f:
                f.write(self.to_gpx(day))
                f.close()
            
    
if __name__=="__main__":
    use_google_maps_api = args.use_google_maps_api
    config_file = args.config

    if use_google_maps_api == None:
        use_google_maps_api = False

    LIFEToTrackConverter(config_file, use_google_maps_api)
 