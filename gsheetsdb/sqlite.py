from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import datetime
import sqlite3

from gsheetsdb.convert import convert_rows
from gsheetsdb.query import get_description_from_payload, run_query
from gsheetsdb.url import extract_url, get_url


# Google Spreadsheet types to SQLite types
typemap = {
    'string': 'text',
    'number': 'real',
    'boolean': 'boolean',
    'date': 'date',
    'datetime': 'timestamp',
    'timeofday': 'timeofday',
}


def adapt_timeofday(timeofday):
    return (
        3600e6 * timeofday.hour + 
        60e6 * timeofday.minute +
        1e6 * timeofday.second +
        timeofday.microsecond
    )


def convert_timeofday(val):
    val = int(val)
    hour, val = divmod(val, int(3600e6))
    minute, val = divmod(val, int(60e6))
    second, val = divmod(val, int(1e6))
    microsecond = int(val)
    return datetime.time(hour, minute, second, microsecond)


sqlite3.register_adapter(datetime.time, adapt_timeofday)
sqlite3.register_converter('timeofday', convert_timeofday)


def create_table(cursor, table, payload):
    cols = ', '.join(
        '"{name}" {type}'.format(name=col['label'], type=typemap[col['type']])
        for col in payload['table']['cols']
    )
    query = 'CREATE TABLE "{table}" ({cols})'.format(table=table, cols=cols)
    cursor.execute(query)


def insert_into(cursor, table, payload):
    cols = payload['table']['cols']
    values = ', '.join('?' for col in cols)
    query = 'INSERT INTO "{table}" VALUES ({values})'.format(
        table=table, values=values)
    rows = convert_rows(cols, payload['table']['rows'])
    cursor.executemany(query, rows)


def execute(query, headers=0, credentials=None):
    # fetch all the data
    from_ = extract_url(query)
    baseurl = get_url(from_, headers)
    payload = run_query(baseurl, 'SELECT *', credentials)

    # create table
    conn = sqlite3.connect(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    create_table(cursor, from_, payload)
    insert_into(cursor, from_, payload)
    conn.commit()

    # run query in SQLite instead
    results = conn.execute(query).fetchall()

    # get description from payload
    description = get_description_from_payload(payload)

    return results, description
