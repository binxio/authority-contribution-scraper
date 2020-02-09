import os
import logging
from flask import jsonify
from authority import loader

from flask import Flask

app = Flask(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
)


@app.route("/")
def run():
    return jsonify(loader.main())


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
