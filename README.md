# LIFE Converter

Tool to convert [LIFE](https://github.com/domiriel/LIFE) format files into GPX Track files

## Introduction

The [LIFE](https://github.com/domiriel/LIFE) file format serves as a way to easily express and register a day in a lifelogging context. It is intended to be both machine- and human-readable, easy to understand and easy to update.

## Concepts

A lifelog is the collection of said personal
data to create a record (with varying degrees of detail) about one’s life. The idea is to create a personal database of our life, that can then
be accessed and analyzed to fit any particular needs we might have.

A format was created in order to assign meaning to periods of time. In this case, these periods correspond to the intervals of time where a user was indoors. This format is named [LIFE](https://github.com/domiriel/LIFE), and it allows for a simple way to annotate trips and stays in locations. The format is designed to be easy to understand by humans,and is displayed in a plain text file. This allows users to edit the document in a easy and straight forward way, with no previous programming knowledge

If done properly, from a [LIFE](https://github.com/domiriel/LIFE) file a user should be able to tell where they were at any given moment in time and (if annotated with semantics) what was the purpose of the visit. Categories and tags can also help with this: a place categorized as a restaurant will probably be visited for a meal. It is up to each user to decide what different tags, categories, etc. represent. One person could use tags to annotate the names of people met at a given place. Another could use it to note where dinner or lunch were had, etc.

## Goal

The goal of this tool is to be able to convert days described in the [LIFE](https://github.com/domiriel/LIFE) format into files that simulate real world routes in a GPX format file. This way we can provide a way to visualize these days whether or not the locations coordinates are explicitly defined in the [LIFE](https://github.com/domiriel/LIFE) file. This allows for the use of the data without comprimising the user's privacy. A LIFE file generator is also provided in order to create completely randomized LIFE files.

## Config

A few parameters can be adjusted in a JSON file that can be passed as a parameter when launching the program.

- **input_path**: defines the directory where the [LIFE](https://github.com/domiriel/LIFE) files are located
- **output_path**: defines the directory where the .gpx files will be generated to
- **google_maps_api_key**: Google Maps Platform API key 
- **tom_tom_api_key**: TomTom Routing API key (default API used)
- **bounds**: defines the max bounds where random coordinates will be generated

Example:
```
{ 
    "point1": {
        "lat": 39.038058, 
        "lng": -9.377571
    },
    "point2": {
        "lat": 38.713286,
        "lng": -9.125020
    }
}
```
- **avg_speed**: defines the speed used to calculate distance bounding boxes between random locations (in km/h)
- **bounds_iterations**: number of times the algorithm will run in order to better define random coordinates for the locations based on how long it takes to travel between them in the [LIFE](https://github.com/domiriel/LIFE) file
- **life_generator**
    - **locations_csv**: defines the path of the [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) file with the locations that will be used to generate the LIFE file
    - **header_path**: defines the path of the input file where you can insert the meta commands that can be placed in the LIFE file's header
    - **output_path**: defines the directory of the output LIFE file that is generated

An API key must be defined. If one API is selected, but the key for said API is not defined, the other will be used instead (provided that key is defined). If none are defined, the program won't work, as they are used to generate routes between 2 points.

You should also define the input and output paths to use the converter, as well as the output path and the path for a [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) file populated with location names in order to use the LIFE generator. 

## Run Converter

The program can be run by using the following commands in the terminal:

```
 $ python life_to_track_converter.py [--help] [--config "file name"] [--google] 
```

or

```
$ python life_to_track_converter.py [-h] [-c "file name"] [-g] 
```

Arguments:
- **help** (--help, -h)
- **config** (--config, -c): defines the configurations json file location  
- **google** (--google, -g): when used, defines the Google Maps API as the prefered API to use (default is Tom Tom Routing API)

## Run Generator

To generate random LIFE files, the following command can be used in the terminal:

```
 $ python life_generator.py [--help] [--config "file name"] [--n_days n] [--max_spans s] [--date "yyyy-mm-dd"] [--output "file name"]
```

or

```
$ python life_generator.py [-h] [-c "file name"] [-n n] [-s s] [-d "yyyy-mm-dd"] [-o "file name"]

```

Keep in mind that the output path and the path for a [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) file populated with location names should be defined in your config json file in order to use this script.

Arguments:
- **help** (--help, -h)
- **config** (--config, -c): defines the configurations json file location  
- **n_days** (--n_days, -n): defines the number of days to generate (100 by omission) 
- **max_spans** (--max_spans, -s): defines the maximum number of spans per day (10 by omission)
- **date** (--date, -d): defines the start date of the generated days (current day by omission)
- **output** (--output, -o): defines the name of the output file ("generated_life" by omission)

