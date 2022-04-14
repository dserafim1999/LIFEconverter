from math import radians, cos, sin, asin, acos, pi, degrees
from rtreelib import Rect #might be able to implement on my own in location_coords
 
'''
TODO give credit to sources 
'''

MIN_LAT = radians(-90)
MAX_LAT = radians(90)
MIN_LNG = radians(-180)
MAX_LNG = radians(180)

EARTH_RADIUS = 6378.1  # kilometers

def coords_obj(lat, lng, time=None):
    ''' Creates a dictionary that defines a point's coordinates
    Args:
        lat (float): point's latitude (in degrees)
        lng (float): point's longitude (in degrees)
        time (string, optional): coordinate's timestamp
    Returns:
        :obj:`dict`: Point's coordinates
    '''

    if time == None:
        return {'lat': lat , 'lng': lng}
    else:
        return {'lat': lat , 'lng': lng, 'time': time}
        
def check_bounds(point):
    ''' Raises exception if points have invalid coordinates
    Args:
        point (:obj:`dict`:): point's coordinates
    '''
    
    lat = radians(point['lat'])
    lng = radians(point['lng'])
    if (lat < MIN_LAT or lat > MAX_LAT or lng < MIN_LNG or lng > MAX_LNG):
        raise Exception("Illegal arguments")
        
def distance_to(point1, point2, radius=EARTH_RADIUS):
    ''' Calculates the distance between 2 points on a sphere
    Args:
        point1 (:obj:`dict`:): coordinates of first point
        point2 (:obj:`dict`:): coordinates of second point
        radius (float): sphere's radius
    Returns:
        float: distance between both points (in km)
    '''

    lat1 = radians(point1['lat'])
    lat2 = radians(point2['lat'])
    lng1 = radians(point1['lng'])
    lng2 = radians(point2['lng'])

    return radius * acos(
            sin(lat1) * sin(lat2) +
            cos(lat1) * 
            cos(lat2) * 
            cos(lng1 - lng2)
        )
        
def bounding_locations(point, distance, radius=EARTH_RADIUS):
    ''' Creates a bounding box of points that are within a certain distance from a point on a sphere
    Args:
        point (:obj:`dict`:): point's coordinates
        distance (float): distance (in km) to analyse
        radius (float): sphere's radius
    Returns:
        :obj:`tuple`: of :obj:`dict`: pair of coordinates that define the bounds of points within a certain distance from the point
    '''
    
    if radius < 0 or distance < 0 or check_bounds(point):
        raise Exception("Illegal arguments")
        
    # angular distance in radians on a great circle
    rad_dist = distance / radius
    
    min_lat = radians(point['lat']) - rad_dist
    max_lat = radians(point['lat']) + rad_dist
    
    if min_lat > MIN_LAT and max_lat < MAX_LAT:
        delta_lng = asin(sin(rad_dist) / cos(radians(point['lat'])))
        
        min_lng = radians(point['lng']) - delta_lng
        if min_lng < MIN_LNG:
            min_lng += 2 * pi
            
        max_lng = radians(point['lng']) + delta_lng
        if max_lng > MAX_LNG:
            max_lng -= 2 * pi

    # a pole is within the distance
    else:
        min_lat = max(min_lat, MIN_LAT)
        max_lat = min(max_lat, MAX_LAT)
        min_lng = MIN_LNG
        max_lng = MAX_LNG
    
    return ( {'lat': degrees(min_lat) , 'lng': degrees(min_lng)} , {'lat': degrees(max_lat) , 'lng': degrees(max_lng)})

def bounding_box(bounds):
    """Creates bounding box from two points that define bounds
    Args:
        bounds(:obj:`tuple`: of :obj:`dict`:): pair of coordinates that define the bounds
    Returns:
        rtreelib.Rect(float, float, float, float): with bounding box min lat, min lon, max lat and max lon
    """

    min_lat = min(bounds[0]["lat"], bounds[1]["lat"])
    min_lng = min(bounds[0]["lng"], bounds[1]["lng"])
    max_lat = max(bounds[0]["lat"], bounds[1]["lat"])
    max_lng = max(bounds[0]["lng"], bounds[1]["lng"])

    return Rect(min_lat, min_lng, max_lat, max_lng)
    
def bounds_intersection(bounds1, bounds2):
    """ Calculates the bounds that result from the intersection of two set of bounds
    Args:
        bounds1(:obj:`tuple`: of :obj:`dict`:): pair of coordinates that define the first bounds
        bounds2(:obj:`tuple`: of :obj:`dict`:): pair of coordinates that define the second bounds
    Response:
        :obj:`tuple`: of :obj:`dict`: pair of coordinates that define the result of intersecting two bounds
    """
    bounding_box1 = bounding_box(bounds1)
    bounding_box2 = bounding_box(bounds2)

    intersection = bounding_box1.intersection(bounding_box2)

    if intersection == None:
        return bounds2
    else:
        return (coords_obj(intersection.min_x, intersection.min_y), coords_obj(intersection.max_x, intersection.max_y))

def is_point_in_bounds(point, bounds):
    """ Determines if a point is within certain bounds
    Args:
        point(:obj:`dict`:): point's coordinates
        bounds(:obj:`tuple`: of :obj:`dict`:): pair of coordinates that define the bounds
    Response:
        Boolean: True if point is in bounds, False if not
    """
    min_lat = min(bounds[0]["lat"], bounds[1]["lat"])
    min_lng = min(bounds[0]["lng"], bounds[1]["lng"])
    max_lat = max(bounds[0]["lat"], bounds[1]["lat"])
    max_lng = max(bounds[0]["lng"], bounds[1]["lng"])

    lat = point['lat']
    lng = point['lng']

    return (lat > min_lat and max_lat > lat) and (lng > min_lng and max_lng > lng)
