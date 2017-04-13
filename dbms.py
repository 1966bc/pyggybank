#!/usr/bin/env python
#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   dbms.py
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   29/05/2015
# version:  0.4
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007                      
# license: wxWindows License 
#-----------------------------------------------------------------------------

"""
This module provides the database class for pyggybank.

"""

import sqlite3 as lite
import sys
import os
from string import strip


class DBMS(object):
    """this class manage all database operation"""

    def __init__(self,):
        super(DBMS, self).__init__()

        """Initialize the class.
          Create a sql statement dictionary
          and open the connection
        """

        
        self.dict_queries = {'flows':"SELECT  event_id,\
                                   flow,\
                                   supplier,\
                                   category,\
                                   settled,\
                                   reference,\
                                   bill,\
                                   strftime('%d-%m-%Y',issued)\
                             FROM flows\
                             WHERE flow LIKE ?\
                             AND settled LIKE ?\
                             AND enable LIKE ?\
                             AND supplier_id LIKE ?\
                             AND category_id LIKE ?\
                             AND issued >=?\
                             ORDER BY issued DESC",
                    'report':"SELECT supplier,\
                                       category,\
                                       reference,\
                                       flow,\
                                       settled,\
                                       strftime('%d-%m-%Y',issued),\
                                       bill\
                               FROM flows\
                               WHERE flow LIKE ?\
                               AND settled LIKE ?\
                               AND enable LIKE ?\
                               AND supplier_id LIKE ?\
                               AND category_id LIKE ?\
                               AND issued >=?\
                               ORDER BY issued DESC",
                    'suppliers':"SELECT * FROM suppliers ORDER BY supplier",
                    'categories':"SELECT * FROM categories ORDER BY category",
                    'cbo_suppliers':"SELECT * FROM suppliers WHERE enable =1 ORDER BY supplier",
                    'cbo_categories':"SELECT * FROM categories WHERE enable =1 ORDER BY category",
                    'category':"SELECT category FROM categories WHERE category_id =?",
                    'supplier':"SELECT supplier FROM suppliers WHERE supplier_id =?",
                    'delete_transaction':"DELETE FROM events WHERE event_id = ?",}

        self.open_connection(os.path.join(os.getcwd(),"pyggy.db"))
        
    def __str__(self):
        return "class: %s\ncon: %s\nqueries: %s" % (self.__class__.__name__,
                                                    self.con,
                                                    len(self.dict_queries))

    def open_connection(self,path):
       
        self.con = lite.connect(path,
                                detect_types=lite.PARSE_DECLTYPES|lite.PARSE_COLNAMES,
                                isolation_level = 'IMMEDIATE')
        

    def write(self, sql, args=()):
        """Write record on database...
           
            @sql : a valid sql statement
            #args: sql arguments if are
            @return: nothing
            @rtype: nothing
        """
        
        try:
            cur = self.con.cursor()
            cur.execute(sql,args)
            self.con.commit()
            
        except:
            self.con.rollback()
            print sys.exc_info()[0]
            print sys.exc_info()[1]
            print sys.exc_info()[2]
        finally:
            try:
                cur.close()
            except:
                print sys.exc_info()[0]
                print sys.exc_info()[1]
                print sys.exc_info()[2]
                

    def read(self, fetch, sql, args=()):

        """Write record on database

            #fetch: True/False = fetchall/fetchone
            @sql : a valid sql statement
            #args: sql arguments if are
            @return: recordset 
            @rtype: tuple
        """
       
        try:
            cur = self.con.cursor()
            cur.execute(sql,args)

            if fetch == True:
                rs =  cur.fetchall()
            else:
                rs =  cur.fetchone()
            cur.close()                
            return rs

        except:
            print sys.exc_info()[0]
            print sys.exc_info()[1]
            print sys.exc_info()[2]           
             

    def get_selected(self,table,field,*args):
        """get a record and return  a dictionary
           used when we click on a row on list ctrl

            #table: table name on database
            @field : is the primary key field
            #*args: something like (1,)
            @return: a dictionary 
            @rtype: dict
        """
        
        record = {}
        sql = "SELECT * FROM %s WHERE %s = ?" % (table,field)
        
        for k,v in enumerate(self.read(False,sql,args)):
            record[k]=v
            #print k,v

        return record

    def get_pk_name(self, table):

        sql = 'SELECT * FROM %s ' % table
        cur = self.con.cursor()
        cur.execute(sql)
        ret = cur.description[0][0]
        cur.close()
        return ret
    
            
        

    def get_combo_id(self,caller,id):
        """get primary key of a record selected on a combo
           
            #caller: the reference to the frame the use this callback, self
            @id : id of the combo widget in the frame
            @return: a primary key
            @rtype: int
        """
        return int(caller.FindWindowById(id).GetClientData(int(caller.FindWindowById(id).GetSelection()))[0])

        
    def get_fields(self,table):
        """this function return fields name of the args table ordered by field number
           
            #table: the table we want know the fields name
            @return: fileds name
            @rtype: list
        """
        
        columns = []
        ret = []

        sql = 'SELECT * FROM %s ' % table
        cur = self.con.cursor()
        cur.execute(sql)
        

        for field in cur.description:
            columns.append(field[0])
        cur.close()
        
        for k,v in enumerate(columns):
            if k > 0:
                ret.append(v)
        return ret

    def get_update_sql(self,table,pk):
        """this function recive a table name and his primary key
           and return a  format update sql statement
           
            #table: the table to update
            @pk : the primary key field name
            @return: an sql formated statement
            @rtype: string
        """
        
        return "UPDATE %s SET %s =? WHERE %s =?"%(table," =?, ".join(self.get_fields(table)),pk)
    

    def get_update_sql_args(self, args, item):
        l = list(args)
        l.append(item)
        return tuple(l)    

    def get_insert_sql(self,table,n):
        """this function recive a table name
            and the len of a list of arguments
            and return a  format insert sql statement
           
            #table: the table where we insert the record
            @n : the len of a list of arguments
            @return: an sql formated statement
            @rtype: string
        """
        return "INSERT INTO %s(%s)VALUES(%s)"%(table,",".join(self.get_fields(table)), ",".join("?"*n))

    def set_combo(self,d,caller):
       
        """this function populate one o more combos reciving a dictionary 
           
            #d: {combo widgets id:{a dict to store sql results},sql,args,True/None,}
            #caller: the reference to the frame the use this callback, self
            @return: a dictionary
            @rtype: dict
        """
       
        for k, v in d.iteritems():
            #print k,v
            rs = self.read(True, v[1],v[2])
            if v[3]is not None:
                rs.insert(0,(0,u'Nothing'))
            for i in rs:
                pk =int(i[0])
                showed = (strip(str(i[1].encode("latin1"))))
                caller.FindWindowById(k).Append (showed,(pk, showed))
            for value in range(caller.FindWindowById(k).GetCount()):
                combo_row = caller.FindWindowById(k).GetClientData(value)
                key = int(combo_row[0])
                v[0][key]=value
        
    
   
def main():

    bar = DBMS()
    print bar
    sql = "SELECT name FROM sqlite_master WHERE type = 'table'"
    rs = bar.read(True, sql)
    if rs:
        for i in enumerate(rs):
            print i           
    raw_input('end')
       
if __name__ == "__main__":
    main()


    
