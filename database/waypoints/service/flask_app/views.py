# -*- coding: utf-8 -*-
"""Flask app for accepting GPS tracking data.

It is best to just use docker-compose from the parent directory.

    $ cd .. && docker-compose up

"""
import datetime
import json
import logging
import sys

import time
import inspect

from flask import Flask, request

import controller
import models
import cache

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

# >> The application is a small service.
APP = Flask(__name__)


SECRET = "hello"

# Timer function for getting time when return values are needed
def timed(f:callable):
    start = time.time()
    ret = f()
    elapsed = (time.time() - start)
    source_code=inspect.getsource(f).strip('\n')
    APP.logger.info(source_code+":  "+str(elapsed)+" seconds")
    return ret


@APP.route("/initialize_db/", methods=["POST"])
def initialize_db():
    """bootstrap_endpoint

    Bootstraps the database using the models.initialize_db() method.

    Returns:
        dict, 201 response code: success
        dict, 500 response code: failure

    """
    secret_key = request.get_json()
    if secret_key["key"] == SECRET:
        models.initialize_db()
        exists = models.db_exists(models.DB_NAME)
        routes_table_exists = models.table_exists("routes")
        route_lengths_exists = models.table_exists("route_lengths")
        assert exists == routes_table_exists == route_lengths_exists
        APP.logger.info("PostGres DB with tables is online.")
        return (
            json.dumps({"Success!": "PostGres DB with postgis extensions is created."}),
            201,
        )
    APP.logger.warn("Error! Failed to initialize the db.")
    return json.dumps({"Error": "Failed to initialize the db"}), 500


@APP.route("/route/", methods=["POST"])
def create_route():
    """route_endpoint

    >> The service accepts data from a GPS tracker device.
    >> Devices request a new route to be started.
    """
    APP.logger.debug("New route_id requested.")
    new_route = timed(lambda:controller.create_route())
    APP.logger.debug("New route_id assigned: %s.", new_route)
    return json.dumps(new_route), 201


@APP.route("/route/<int:route_id>/way_point/", methods=["POST"])
def add_way_point(route_id):
    """route_add_way_point_endpoint

    >> Devices will continuously populates the route with data points
    >> in the form of WGS84 coordinates.
    >> Devices are expected to finish their route within a day.
    >> After a day, the device can not add more data points.

    Args:
        route_id (int): A route_id supplied by the device in a POST

    Returns:
        dict, 201 response code:
        dict, 404 response code: if the route_id does not exist in the dict, route_lengths table
        dict, 403 response code: if the creation time of the route_id is older than today
    """
    coordinates = request.get_json()
    assert "lat" in coordinates# Good! Sanitize the input. Check that this is
    assert "lon" in coordinates# done elsewhere in the code. It is good!

    return timed(lambda: controller.update_route(route_id, coordinates["lon"], coordinates["lat"]))


@APP.route("/route/<int:route_id>/length/")
def calculate_length(route_id):
    """route_length_endpoint

    >> Users can request the length of a route. The service allows
    for route length request even while the route is in progress.

    Args:
        route_id (int): A route_id supplied by the user in a POST

    Returns:
        dict, 201 response code: success
        dict, 404 response code: if the route_id has no waypoints
    """
    route_id_has_waypoints = controller.route_id_has_waypoints(route_id)
    if not route_id_has_waypoints:
        return (
            json.dumps(
                {"Error": "route_id {} has not added any waypoints".format(route_id)}
            ),
            404,
        )
    length_of_route = timed(lambda:controller.get_length_of_single_route(route_id))
    return json.dumps({"route_id": route_id, "km": length_of_route[0]}), 201


@APP.route("/longest-route/<string:query_date>")
def calculate_longest_route_for_day(query_date):
    """route_longest_route_in_day_endpoint

    >> Users can request the route_id that corresponds to the longest path
    >> for any past day. Errors are thrown if the data is not in the past.

    Args:
        query_date (str): in the form of %Y-%m-%d

    Returns:
        dict, 201 response code: if there were waypoints for query_date older than today
        dict, 403 response code): if the route_id was created today
        dict, 404 response code: if there are no waypoints for query_date
    """
    if cache.query_date_is_in_cache(query_date):# This is a ram op #1
        return (
            json.dumps(
                {
                    "date": query_date,
                    "route_id": cache.LONGEST_ROUTE_IN_DAY[query_date][0],
                    "km": cache.LONGEST_ROUTE_IN_DAY[query_date][1],
                }
            ),
            201,
        )
    query_older_than_today = \
        controller.is_query_date_older_than_today(query_date)# ram op #2

    if not query_older_than_today:
        return (
            json.dumps({"Error": "The request will only query days in the past."}),
            403,
        )
    # This is db lookup #1
    longest_route_in_a_day = timed(lambda: controller.query_longest_route_in_day())

    if longest_route_in_a_day:
        APP.logger.info("Updating longest route in day: {}/{}.".format(query_date, longest_route_in_a_day))
        cache.update_long_route_cache(query_date, longest_route_in_a_day)
        return (
            json.dumps(
                {
                    "date": query_date,
                    "route_id": longest_route_in_a_day[0],
                    "km": longest_route_in_a_day[1],
                }
            ),
            201,
        )
    # It is possible that there were no routes for query_date.
    return (json.dumps({"Error": "No routes recorded for {}".format(query_date)}), 404)


if __name__ == "__main__":
    APP.run(host="0.0.0.0", debug=True)
