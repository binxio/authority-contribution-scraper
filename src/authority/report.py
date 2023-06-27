"""
Module containing the Report class
"""
import logging
import os
import tempfile
from io import BytesIO

import gcloud_config_helper
import google
import numpy
from google.cloud import bigquery
from matplotlib import pyplot


class Report:
    """
    Class for reporting on contributions
    """

    def __init__(self, unit: str = ""):
        if gcloud_config_helper.on_path():
            credentials, project = gcloud_config_helper.default()
        else:
            logging.info("using application default credentials")
            credentials, project = google.auth.default()
        self.client = bigquery.Client(credentials=credentials, project=project)
        self.unit = unit

    def get_contributions_per_month(self) -> BytesIO:
        """
        Writes a plot of the contributions per month for the current calendar year
        to a BytesIO stream

        :return: A BytesIO stream containing an image
        :rtype: :obj:`BytesIO`
        """
        x_labels = []
        blogs = []
        xkes = []
        pull_requests = []

        job = self.client.query(_CONTRIBUTIONS_PER_MONTH.format(unit=self.unit))
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

        image = BytesIO()
        pyplot.savefig(image, format="png")
        pyplot.close()
        image.seek(0)
        return image

    def print_authors(self):
        """
        Queries the BigQuery table and prints out the number of contributions per author
        """
        job = self.client.query(_AUTHORS.format(unit=self.unit))
        authors = [f'{row.get("author")} ({row.get("aantal")})' for row in job.result()]
        print(", ".join(authors).replace(" (1)", ""))


_CONTRIBUTIONS_PER_MONTH = """
               SELECT *
               FROM (
               SELECT DATETIME_TRUNC(date, MONTH) AS maand, type, COUNT(DISTINCT guid) AS aantal,
               FROM `binxio-mgmt.authority.contributions` c, `binxio-mgmt.authority.contributors` a 
               WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) AND CURRENT_DATE() 
               AND c.author = a.author
               AND ('{unit}' = '' or a.unit = '{unit}')
               GROUP BY maand, type
               ) 
               PIVOT ( 
                   MAX(aantal)
                   FOR type IN ('xke', 'blog', 'github-pr' AS pullrequest)
               )
               ORDER BY maand ASC
       """

_AUTHORS = """
               SELECT c.author, COUNT(DISTINCT guid) AS aantal,
               FROM `binxio-mgmt.authority.contributions` c, `binxio-mgmt.authority.contributors` a
               WHERE date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH) AND 
               DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 0 MONTH)
               AND c.author = a.author
               AND ('' = '{unit}' or a.unit = '{unit}')
               GROUP BY c.author
               ORDER BY aantal DESC, author ASC
       """


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="report authority contributions")
    parser.add_argument("--unit", default="", type=str, help="to report on")
    args = parser.parse_args()

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
    )
    reporter = Report(args.unit)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False, mode="wb") as file:
        image_stream = reporter.get_contributions_per_month()
        file.write(image_stream.read())
        print(file.name)
    reporter.print_authors()
