import argparse
from datetime import datetime
from random import randrange, sample
import sys
import life.life as life 

import argparse, json
from os.path import expanduser, isfile, join
from os import rename
import csv

from utils.utils import update_dict
from utils.default_config import CONFIG

MAX_MINS_PER_DAY = 1440
FAIL_COLOR = '\033[91m'
END_COLOR = '\033[0m'

def pairwise(iterable):
    a = iter(iterable)
    return zip(a, a)

parser = argparse.ArgumentParser(description='')
parser.add_argument('--config', '-c', dest='config', metavar='c', type=str,
        help='configuration file')
parser.add_argument('--n_days', '-n', dest='n_days', metavar='n', type=int,
        help='number of days to generate')
parser.add_argument('--max_spans', '-s', dest='max_spans', metavar='s', type=int,
        help='max number of spans per day')
parser.add_argument('--date', '-d', dest='date', metavar='d', type=str,
        help='start date (YYYY-MM-DD)')
parser.add_argument('--output', '-o', dest='output', metavar='o', type=str,
        help='output file name')
args = parser.parse_args()


class LIFEGenerator(object):
    """ 
    Generates a random LIFE file to generate data
    """

    def __init__(self, config_file, n_days, max_spans, start_date, output):
        self.config = dict(CONFIG)
        if config_file and isfile(expanduser(config_file)):
            with open(expanduser(config_file), 'r') as config_file:
                config = json.loads(config_file.read())
                update_dict(self.config, config)

        self.n_days = n_days if n_days != None else 100
        self.max_spans = max_spans if max_spans != None else 10
        self.locations = []
        self.header = ''
        
        date = datetime.strptime(start_date, '%Y-%m-%d') if start_date != None else datetime.now()
        self.cur_date = str(date.date()).replace('-','_')

        output_file = output if output != None else "generated_life"

        self.get_locations()
        self.generate_file(output_file)

    def get_locations(self):
        """
            Extracts locations from CSV file with the path provided in the config file
        """
        locations_csv = join(expanduser(self.config['life_generator']['locations_csv']))

        if isfile(locations_csv):
            with open('input\generator\locations.csv','r') as csvfile: 
                reader = csv.reader(csvfile, delimiter=',', quotechar='|') 
                for row in reader:
                    self.locations += row
        else:
            sys.exit(f"{FAIL_COLOR}Please provide a CSV file with location names.{END_COLOR}")

    def get_header(self):
        """
            Appends the header file with meta commands to the top of the generated LIFE file
        """

        header_path = join(expanduser(self.config['life_generator']['header_path']))

        if isfile(header_path):
            header = open(header_path, 'r').read()
            self.file.write(header + '\n')            

    def generate_file(self, file_name):
        """
            Creates file with the provided path and file name with the generated LIFE days
            Args:
                file_name (str): defines the name of the generated file 
        """

        self.file = open(join(expanduser(self.config['life_generator']['output_path']), file_name + '.life'), "w")

        # adds header with meta commands to file (if header file is provided)
        self.get_header()
        
        for i in range(self.n_days):
            self.generate_day()
            self.cur_date = life.tomorrow(self.cur_date)
        
        self.file.close()

    def generate_day(self):
        """
            Generates a day in the LIFE fromat
        """
        day = [f'--{self.cur_date}', '\n']
        times = self.generate_times_for_spans()
        
        # iterates through pairs of times that will compose a span
        for start, end in pairwise(times):
            # attributes a random location to a span
            day.append(f'{start}-{end}: {self.locations[randrange(0, len(self.locations) - 1)]}') 
            day.append('\n')

        day.append('\n')

        # writes day in LIFE file
        self.file.writelines(day)

    def generate_times_for_spans(self):
        """
            Generates the times that will be used to create the spans in a LIFE day (including 00:00 and 23:59)
        """
        start_end_times = ['0000', '2359']
        
        # the max times to generate is half the max num of spans (spans have 2 start and end times) minus the start and end of day times we already know
        max_times = max(self.max_spans * 2, 2)

        # calculates even random number of times to generate  
        n_times = max(randrange(0, max_times, 2), 2)
        
        # generates n_times of times to use in spans
        times = sample(range(0, MAX_MINS_PER_DAY), n_times)

        # converts minutes in day to military time
        military_times = list(map(lambda mins: life.minutes_to_military(mins), times))
        
        # return all times in military format that will compose the spans of a day
        return sorted(military_times + start_end_times)

if __name__=="__main__":
    LIFEGenerator(args.config, args.n_days, args.max_spans, args.date, args.output)