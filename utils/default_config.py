"""
Base line settings
"""

CONFIG = {
    "input_path": None,
    "output_path": None,
    "google_maps_api_key": "",
    "tom_tom_api_key": "",
    "bounds": { # represents the corners of the bounds where random locations will be generated
        "point1": {
            # "lat": 38.746898,
            # "lng": -9.157293
            "lat": 39.038058, 
            "lng": -9.377571
        },
        "point2": {
            "lat": 38.713286,
            "lng": -9.125020
        }
    },
    "avg_speed": 10, # speed used to determine bounds of possible points
    "bounds_iterations": 100 # number of iterations the algorithm will try to tighten possible point bounds
}
