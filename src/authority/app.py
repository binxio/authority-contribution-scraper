"""
Module containing the Flask app for the Authority Contribution Scraper
"""
import logging
import os

from flask import Flask, send_file
from flask import jsonify
from flask_caching import Cache

from authority import loader
from authority.report import Report

cache = Cache(config={"CACHE_TYPE": "SimpleCache"})

app = Flask(__name__)
cache.init_app(app)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
)


@app.route("/scrape")
def scrape():
    """
    Scrapes authority contributions from authoritative sources (i.e. blog, XKE app) and stores the
    results in BigQuery.
    """
    return jsonify(loader.main())


@app.route("/graph/contributions-per-month")
@cache.cached(timeout=3600)
def contributions_per_month():
    """
    generates a graph of the number of contributions per month in this calendar year.
    """
    reporter = Report()
    image = reporter.get_contributions_per_month()
    image.seek(0)
    return send_file(image, mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
