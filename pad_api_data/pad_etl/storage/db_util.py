import logging
import random

import pymysql

from .sql_item import SqlItem, _col_compare, _tbl_name_ref, process_col_mappings


logger = logging.getLogger('database')
logger.setLevel(logging.ERROR)


class DbWrapper(object):
    def __init__(self, dry_run: bool=True):
        self.dry_run = dry_run
        self.connection = None

    def connect(self, db_config):
        logger.debug('DB Connecting')
        self.connection = pymysql.connect(host=db_config['host'],
                                          user=db_config['user'],
                                          password=db_config['password'],
                                          db=db_config['db'],
                                          charset=db_config['charset'],
                                          cursorclass=pymysql.cursors.DictCursor,
                                          autocommit=True)
        logger.info('DB Connected')

    def execute(self, cursor, sql):
        logger.debug('Executing: %s', sql)
        return cursor.execute(sql)

    def fetch_data(self, sql):
        with self.connection.cursor() as cursor:
            self.execute(cursor, sql)
        return list(cursor.fetchall())

    def load_to_key_value(self, key_name, value_name, table_name, where_clause=None):
        with self.connection.cursor() as cursor:
            sql = 'SELECT {} AS k, {} AS v FROM {}'.format(key_name, value_name, table_name)
            if where_clause:
                sql += ' WHERE ' + where_clause
            self.execute(cursor, sql)
            data = list(cursor.fetchall())
            return {row['k']: row['v'] for row in data}

    def get_single_or_no_row(self, sql):
        with self.connection.cursor() as cursor:
            self.execute(cursor, sql)
            data = list(cursor.fetchall())
            num_rows = len(data)
            if num_rows > 1:
                raise ValueError('got too many results:', num_rows, sql)
            if num_rows == 0:
                return None
            else:
                return data[0]

    def get_single_value(self, sql, op=str, fail_on_empty=True):
        with self.connection.cursor() as cursor:
            self.execute(cursor, sql)
            data = list(cursor.fetchall())
            num_rows = len(data)
            if num_rows == 0:
                if self.dry_run or not fail_on_empty:
                    return None
                raise ValueError('got zero results:', sql)
            if num_rows > 1:
                raise ValueError('got too many results:', num_rows, sql)
            row = data[0]
            if len(row.values()) > 1:
                raise ValueError('too many columns in result:', sql)
            return op(list(row.values())[0])

    def load_single_object(self, obj_type, key_val):
        sql = 'SELECT * FROM {} WHERE {}'.format(
            _tbl_name_ref(obj_type.TABLE),
            _col_compare(obj_type.KEY_COL))
        sql = sql.format(**{obj_type.KEY_COL: key_val})
        data = self.get_single_or_no_row(sql)
        return obj_type(**process_col_mappings(obj_type, data)) if data else None

    def load_multiple_objects(self, obj_type, key_val):
        sql = 'SELECT * FROM {} WHERE {}'.format(
            _tbl_name_ref(obj_type.TABLE),
            _col_compare(obj_type.LIST_COL))
        sql = sql.format(**{obj_type.LIST_COL: key_val})
        data = self.fetch_data(sql)
        return [obj_type(**process_col_mappings(obj_type, d)) for d in data]

    def check_existing(self, sql):
        with self.connection.cursor() as cursor:
            num_rows = self.execute(cursor, sql)
            if num_rows > 1:
                raise ValueError('got too many results:', num_rows, sql)
            return bool(num_rows)

    def check_existing_value(self, sql):
        with self.connection.cursor() as cursor:
            num_rows = self.execute(cursor, sql)
            if num_rows > 1:
                raise ValueError('got too many results:', num_rows, sql)
            elif num_rows == 0:
                return None
            else:
                row_values = list(cursor.fetchone().values())
                if len(row_values) > 1:
                    return row_values
                else:
                    return row_values[0]

    def insert_item(self, sql):
        with self.connection.cursor() as cursor:
            if self.dry_run:
                logger.warn('not inserting item due to dry run')
                return random.randrange(-99999, -1)
            self.execute(cursor, sql)
            data = list(cursor.fetchall())
            num_rows = len(data)
            if num_rows > 0:
                raise ValueError('got too many results for insert:', num_rows, sql)
            return cursor.lastrowid

    def insert_or_update(self, item: SqlItem):
        key = item.key_value()
        if item.uses_alternate_key_lookup():
            key = self.get_single_value(item.exists_sql(), op=int, fail_on_empty=False)
            item.set_key_value(key)

            if not key:
                logger.info('item (alt) needed insert: %s %s', type(item), key)
                key = self.insert_item(item.insert_sql())
            elif not self.check_existing(item.needs_update_sql()):
                logger.info('item (alt) needed update: %s %s', type(item), key)
                self.insert_item(item.update_sql())

        elif not item.uses_local_primary_key():
            if not self.check_existing(item.exists_sql()):
                logger.info('item (fk) needed insert: %s %s', type(item), key)
                key = self.insert_item(item.insert_sql())
            elif not self.check_existing(item.needs_update_sql()):
                logger.info('item (fk) needed update: %s %s', type(item), key)
                self.insert_item(item.update_sql())
        else:
            if item.needs_insert():
                logger.info('item needed insert: %s %s', type(item), key)
                key = self.insert_item(item.insert_sql())
            elif not self.check_existing(item.needs_update_sql()):
                logger.info('item needed update: %s %s', type(item), key)
                self.insert_item(item.update_sql())
        return key
