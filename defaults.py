# -*- coding: utf-8 -*-

DEFAULT_PREFIX='default'
RESOURCE_TABLE='data'
INDEX_TABLE='index'
INDEX_DEF_TABLE='index_def'
METADATA_TABLE='meta'
METADATA_INDEX_TABLE='meta_idx'
URI_TABLE='uri_map'

DB_DRIVER = "pyPgSQL.PgSQL"
#DB_DRIVER="pgdb"
DB_ARGS = {
    'database':'seishub',
    'user':'seishub',
    'password':'seishub'
    }
# import a db specific exception, raised on some db errors
from pyPgSQL.PgSQL import OperationalError as OperationalError

# the index tables refer to the resource tables (FOREIGN KEY), this is not
# forced by seishub.xmldb, so different databases for indexes and resources
# should easily be possible, if needed
CREATES=["CREATE TABLE %s_%s (id serial8 primary key, xml_data text)" % \
         (DEFAULT_PREFIX, RESOURCE_TABLE),
         ("CREATE TABLE %s_%s (uri text primary key, res_id int8 " + \
         "references %s_%s(id))") % \
         (DEFAULT_PREFIX,URI_TABLE,DEFAULT_PREFIX,RESOURCE_TABLE),
         ("CREATE TABLE %s_%s (id serial8 primary key, " + \
         "key_path text, value_path varchar(50), data_type varchar(10), " + \
         "UNIQUE (key_path,value_path))") % \
         (DEFAULT_PREFIX,INDEX_DEF_TABLE),
         ("CREATE TABLE %s_%s (id serial8 primary key, " + \
         "index_id int8 references %s_%s(id), key text, " + \
         "value int8 references %s_%s(id))") % \
         (DEFAULT_PREFIX, INDEX_TABLE,DEFAULT_PREFIX, INDEX_DEF_TABLE,
          DEFAULT_PREFIX, RESOURCE_TABLE)
         ]

QUERY_STR_MAP={'res_tab':DEFAULT_PREFIX+'_'+RESOURCE_TABLE,
               'uri_tab':DEFAULT_PREFIX+'_'+URI_TABLE
               }

ADD_RESOURCE_QUERY="""INSERT INTO %s_%s (id,xml_data) values (%s,%s)"""
DELETE_RESOURCE_QUERY="""DELETE FROM %(res_tab)s WHERE (id = '%(res_id)s')"""
REGISTER_URI_QUERY="""INSERT INTO %s_%s (res_id,uri) values (%s,%s)"""
REMOVE_URI_QUERY="""DELETE FROM %(uri_tab)s WHERE (uri='%(uri)s')"""
ADD_INDEX_QUERY="INSERT INTO %(prefix)s_%(table)s (id,key_path,value_path,data_type) " + \
                "values (%(id)s,%(key_path)s,%(value_path)s,%(data_type)s)"                
DELETE_INDEX_BY_KEY_QUERY="DELETE FROM %(prefix)s_%(table)s WHERE " + \
                "(value_path=%(value_path)s AND key_path=%(key_path)s)"
DELETE_INDEX_BY_ID_QUERY="DELETE FROM %(prefix)s_%(table)s WHERE (id=%(id)s)"
GET_INDEX_BY_ID_QUERY="SELECT id,key_path, value_path,data_type FROM %(prefix)s_%(table)s " + \
                      "WHERE (id=%(id)s)"
GET_INDEX_BY_KEY_QUERY="SELECT id,key_path,value_path, data_type FROM %(prefix)s_%(table)s " + \
                "WHERE (key_path=%(key_path)s AND value_path=%(value_path)s)"
GET_NEXT_ID_QUERY="""SELECT nextval('%s_%s_id_seq')"""
GET_ID_BY_URI_QUERY="""SELECT res_id FROM %(uri_tab)s WHERE (uri='%(uri)s')"""
GET_RESOURCE_BY_URI_QUERY="""SELECT xml_data FROM %(res_tab)s,%(uri_tab)s
    WHERE(%(res_tab)s.id=%(uri_tab)s.res_id
    AND %(uri_tab)s.uri='%(uri)s')"""




# default components
DEFAULT_COMPONENTS = ('seishub.about', 
                      'seishub.web.admin', 
                      'seishub.web.rest',)