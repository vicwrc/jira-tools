import csv
from collections import namedtuple


def read_csv(filename):
    with open(filename, newline="") as infile:
        reader = csv.reader(infile)
        Data = namedtuple("Data", next(reader))  # get names from column headers
        result = []
        for data in map(Data._make, reader):
            result.append(data)
        return result

