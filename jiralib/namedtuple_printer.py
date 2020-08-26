import csv
import os


def write_csv(filename, header, records, out_folder='out'):
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    with open(out_folder + "/" + filename, mode='w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        csv_writer.writerow(list(header._fields))
        for record in records:
            csv_writer.writerow(list(record))

#TestTuple = namedtuple('TestTuple', 'employee task')
#write_csv("test.csv", TestTuple, [TestTuple('qwe','task1'), TestTuple('asd','task2')])