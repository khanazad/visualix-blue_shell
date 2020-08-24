# -*- coding: utf-8 -*-
"""
cache.py offer simple in-memory key value storage for the app. It is used to
prevent db lookups for the (ugly but effective) LONGEST_ROUTE_IN_DAY query
"""

LONGEST_ROUTE_IN_DAY = {"1984-01-28": [0, 833.77]}

def query_date_is_in_cache(query_date):
    """A simple check that the query date is in the check

    Args:
        query_date (str): in the form of %Y-%m-%d

    """
    return query_date in LONGEST_ROUTE_IN_DAY

def update_long_route_cache(query_date, longest_route_in_a_day):
    """
    >> This information is expected to be highly requested
    If the query date was not in the cache, we update the cache with this
    new information.

    Args:
        query_date (str): %Y-%m-%d format

        longest_route_in_a_day (dict):
            e.g.
            {
            'date' (str): val (str) - date for which the route_id is the longest,
            'route_id': val (int) - id of route,
            'km' (str): val (float) - length in km of route
             }
    """
    LONGEST_ROUTE_IN_DAY.update(
        {query_date: [longest_route_in_a_day[0], longest_route_in_a_day[1]]}
    )
