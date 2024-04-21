import pandas as pd
import sqlite3

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)

    return conn


def df_from_db(db, tablename, cond1, cond2, event):
    con = create_connection(db)

    sql = (f'SELECT * '
           f'FROM {tablename} '
           f'WHERE {cond1} AND {cond2};')
   
    if event: 
        df = pd.read_sql_query(
            sql,
            con, 
            parse_dates = {"starttime": "%Y-%m-%dT%H:%M:%S"}
            )
    else: 
        df = pd.read_sql_query(
        sql,
        con, 
        )
    return(df)


def insert_to_db(input, output, tablename): 
    input = input.reset_index()
    con_local = create_connection(output)
    input.to_sql(tablename, con_local, if_exists='append')

    