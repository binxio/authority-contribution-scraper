import logging
import os
import re
from tempfile import NamedTemporaryFile
from typing import BinaryIO, IO
from google.cloud import bigquery
from google.cloud.bigquery.job import QueryJob
import numpy
import google
import gcloud_config_helper
from matplotlib import pyplot


class Report(object):
    def __init__(self):
        if gcloud_config_helper.on_path():
            credentials, project = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, project = google.auth.default()
        self.client = bigquery.Client(credentials=credentials, project=project)

    def get_contributions_per_month(self, stream: BinaryIO):
        x_labels = []
        blogs = []
        xkes = []
        pull_requests = []

        job: QueryJob = self.client.query(_contributions_per_month)
        for row in job.result():
            x_labels.append(row.get("maand").strftime("%B\n%Y"))
            blogs.append(row.get("blog"))
            xkes.append(row.get("xke"))
            pull_requests.append(row.get("pullrequest"))

        blogs = list(map(lambda c: c if c else 0, blogs))
        xkes = list(map(lambda c: c if c else 0, xkes))
        pull_requests = list(map(lambda c: c if c else 0, pull_requests))

        x_axis = numpy.arange(len(x_labels))
        pyplot.rcParams["figure.figsize"] = (10, 5)
        pyplot.bar(x_axis - 0.2, blogs, 0.4, label="Blogs")
        pyplot.bar(x_axis + 0.2, xkes, 0.4, label="XKEs")
        pyplot.bar(x_axis + 0.4, pull_requests, 0.4, label="Github PRs")
        pyplot.xticks(x_axis, x_labels)
        pyplot.xticks(rotation=90)
        pyplot.title("Contributions per month")
        pyplot.legend()
        pyplot.tight_layout()
        pyplot.savefig(stream, format="png")
        pyplot.close()

    def print_authors(self):
        job: QueryJob = self.client.query(_authors)
        authors = [f'{row.get("author")} ({row.get("aantal")})' for row in job.result()]
        print(re.sub(r" \(1\)", "", ", ".join(authors)))


_contributions_per_month = """
               select *
               from (
               select  datetime_trunc(date, MONTH) as maand ,type, count(distinct guid) as aantal,
               from `binxio-mgmt.authority.contributions` 
               where date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) AND CURRENT_DATE() 
               group by maand, type
               ) 
               PIVOT ( 
                   MAX(aantal)
                   FOR type IN ('xke', 'blog', 'github-pr' as pullrequest)
               )
               order by maand asc
       """

_authors = """
               select  author, count(distinct guid) as aantal,
               from `binxio-mgmt.authority.contributions`
               where date between date_sub(date_trunc(current_date(), month), interval 1 month) and date_trunc(current_date(), month)
               group by author
               order by aantal desc, author asc
       """


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    reporter = Report()
    with NamedTemporaryFile(suffix=".png", delete=False) as filename:
        reporter.get_contributions_per_month(filename.file)
        print(filename.name)
    reporter.print_authors()
