from flask import Flask, jsonify
from flask_cors import CORS
from openfx_api.openfx_api import OpenFxApi
from api.web_options import get_options
import http
import json

from scraping.bloomberg_com import bloomberg_com
from scraping.investing_com import get_pair

app = Flask(__name__)
CORS(app)

def get_response(data):
    if data is None:
        return jsonify(dict(message='error getting data')), http.HTTPStatus.NOT_FOUND
    else:
        return jsonify(data)


@app.route("/api/test")
def test():
    return jsonify(dict(message='hello'))


@app.route("/api/headlines")
def headlines():
    return get_response(bloomberg_com())


@app.route("/api/account")
def account():
    return get_response(OpenFxApi().get_account_summary())


@app.route("/api/options")
def options():
    return get_response(get_options())


@app.route("/api/technicals/<pair>/<tf>")
def technicals(pair, tf):
    return get_response(get_pair(pair, tf))


@app.route("/api/prices/<pair>/<granularity>/<count>")
def prices(pair, granularity, count):
    return get_response(OpenFxApi().web_api_candles(pair, granularity, count))


@app.route("/api/signals")
def get_signals():
    """
    API endpoint to fetch the last 10 signals from signals.json.
    """
    signals_file_path = "logs/signals.json"
    try:
        with open(signals_file_path, "r") as json_file:
            signals = json.load(json_file)
        return jsonify(signals)
    except FileNotFoundError:
        return jsonify({"error": "signals.json file not found."}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to read signals.json: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
