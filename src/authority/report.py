import logging
import os
from tempfile import NamedTemporaryFile
from typing import BinaryIO, IO
from google.cloud import bigquery
from google.cloud.bigquery.job import QueryJob
import numpy
from matplotlib import pyplot


class Report(object):
    def __init__(self):
        self.client = bigquery.Client()

    def get_contributions_per_month(self, stream: BinaryIO):
        x_labels = []
        blogs = []
        xkes = []

        job: QueryJob = self.client.query(_contributions_per_month)
        for row in job.result():
            x_labels.append(row.get("maand").strftime("%B\n%Y"))
            blogs.append(row.get("blog"))
            xkes.append(row.get("xke"))

        blogs = list(map(lambda c: c if c else 0, blogs))
        xkes = list(map(lambda c: c if c else 0, xkes))

        x_axis = numpy.arange(len(x_labels))
        pyplot.bar(x_axis - 0.2, blogs, 0.4, label="Blogs")
        pyplot.bar(x_axis + 0.2, xkes, 0.4, label="XKEs")
        pyplot.xticks(x_axis, x_labels)
        pyplot.title("Contributions per month")
        pyplot.legend()
        pyplot.savefig(stream, format="png")
        pyplot.close()


_contributions_per_month = """
               select *
               from (
               select  datetime_trunc(date, MONTH) as maand ,type, count(distinct guid) as aantal,
               from `binxio-mgmt.authority.contributions` 
               where datetime_trunc(date, year) = datetime_trunc("2022-01-01",year)
               group by maand, type
               ) 
               PIVOT ( 
                   MAX(aantal)
                   FOR type IN ('xke', 'blog')
               )
               order by maand asc
       """

if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    reporter = Report()
    with NamedTemporaryFile(suffix=".png", delete=False) as filename:
        reporter.get_contributions_per_month(filename.file)
        print(filename.name)
