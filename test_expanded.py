"""Regression tests for relational constraints, API scopes and CLI persistence."""
from contextlib import closing, redirect_stdout
from io import StringIO
import sqlite3
import unittest
from unittest.mock import patch
import test_chore_api
from roomies import connect, staff_menu


class ExpandedTest(unittest.TestCase):
    setUp = test_chore_api.ChoreApiTest.setUp
    request = test_chore_api.ChoreApiTest.request

    def call(self,who,kind,method='GET',payload=None,item=None,household=1):
        path=f'/api/database/households/{household}/{kind}'
        if item is not None:
            path+='/'+str(item)
        return self.request(who,household,method,payload,path=path)

    def test_expense_split_persistence_and_cascade(self):
        status,result=self.call('alex','expenses','POST',{'title':'Test bill','amount':'10.00','date':'2026-11-20'})
        self.assertEqual(status,201,result)
        expense=result['expenses'][-1]['id']
        with closing(connect(self.database)) as db:
            shares=db.execute('SELECT user_id,share_amount FROM ExpenseShare WHERE expense_id=? ORDER BY user_id',(expense,)).fetchall()
            self.assertEqual(shares,[(1,3.34),(2,3.33),(3,3.33)])
        self.assertEqual(self.call('mia','expenses','PATCH',{'paid':True},expense)[0],200)
        self.assertEqual(self.call('mia','expenses','DELETE',item=expense)[0],403)
        self.assertEqual(self.call('riley','expenses')[0],403)
        self.assertEqual(self.call('alex','expenses','DELETE',item=expense)[0],200)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ExpenseShare WHERE expense_id=?',(expense,)).fetchone()[0],0)

    def test_database_rejects_cross_household_share_insert_and_update(self):
        with closing(connect(self.database)) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO ExpenseShare VALUES(1,1,4,1,0)')
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('UPDATE ExpenseShare SET user_id=4 WHERE expense_id=1 AND user_id=2')
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO ExpenseShare VALUES(1,2,4,1,0)')

    def test_invalid_expenses_roll_back(self):
        base={'title':'Bill','amount':'20.00','date':'2026-11-20'}
        for change in [{'memberIds':[4]},{'memberIds':[1,1]},{'paidById':4},{'amount':'1.001'},{'date':'2026-02-30'},{'amount':'NaN'}]:
            self.assertEqual(self.call('alex','expenses','POST',{**base,**change})[0],400)
        self.assertEqual(len(self.call('alex','expenses')[1]['expenses']),2)

    def test_announcement_scopes_and_delete(self):
        status,result=self.call('taylor','announcements','POST',{'title':'Meeting','body':'Tonight'})
        self.assertEqual(status,201,result)
        item=result['announcements'][0]['announcement_id']
        self.assertTrue(any(r['announcement_id']==item for r in self.call('mia','announcements')[1]['announcements']))
        self.assertEqual(self.call('casey','announcements')[0],403)
        self.assertEqual(self.call('mia','announcements','DELETE',item=item)[0],403)
        self.assertEqual(self.call('taylor','announcements','DELETE',item=item)[0],200)

    def test_household_create_and_empty_delete(self):
        path='/api/database/households'
        self.assertEqual(self.request('morgan',1,'POST',{'propertyId':1,'unit':'9Z'},path=path)[0],403)
        status,result=self.request('jordan',1,'POST',{'propertyId':1,'unit':'9Z','raId':11},path=path)
        self.assertEqual(status,201,result)
        item=next(r['household_id'] for r in result['households'] if r['unit_label']=='9Z')
        self.assertEqual(self.request('jordan',1,'POST',{'propertyId':1,'unit':'9Z'},path=path)[0],400)
        self.assertEqual(self.request('jordan',1,'DELETE',path=path+'/'+str(item))[0],200)
        self.assertEqual(self.request('jordan',1,'DELETE',path=path+'/1')[0],400)

    def test_leases_scope_overlap_and_active_query(self):
        self.assertEqual(len(self.call('alex','leases')[1]['leases']),1)
        self.assertEqual(len(self.call('jordan','leases')[1]['leases']),3)
        self.assertEqual(self.call('taylor','leases')[0],403)
        payload={'userId':1,'start':'2027-06-01','end':'2028-05-31','rent':'675.00'}
        self.assertEqual(self.call('alex','leases','POST',payload)[0],403)
        status,result=self.call('jordan','leases','POST',payload)
        self.assertEqual(status,201,result)
        self.assertEqual(self.call('jordan','leases','POST',payload)[0],409)
        with closing(connect(self.database)) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO Lease(household_id,user_id,start_date,end_date,monthly_rent) VALUES(1,1,'2026-09-01','2027-01-01',500)")
            sql=(__import__('pathlib').Path(__file__).with_name('queries.sql')).read_text().split('-- 11.')[1]
            query='\n'.join(sql.splitlines()[1:])
            self.assertEqual(db.execute(query).fetchone(),('Cypress Apartments','2A',3,1900.0))
        lease=result['leases'][-1]['lease_id']
        self.assertEqual(self.call('jordan','leases','DELETE',item=lease)[0],200)

    def test_web_history_is_atomic_and_idempotent(self):
        path='/api/requests/manager/1'
        before=self.request('jordan',1,path='/api/requests/manager')[1]['requests'][-1]['history']
        self.assertEqual(self.request('jordan',1,'PATCH',{'status':'In Progress'},path=path)[0],200)
        self.assertEqual(self.request('jordan',1,'PATCH',{'status':'In Progress'},path=path)[0],200)
        self.assertEqual(self.request('morgan',1,'PATCH',{'status':'Closed'},path=path)[0],404)
        self.assertEqual(self.request('jordan',1,'PATCH',{'status':'Closed','note':[]},path=path)[0],400)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT status FROM Request WHERE request_id=1').fetchone()[0],'In Progress')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM RequestUpdate WHERE request_id=1').fetchone()[0],len(before)+1)

    def test_cli_status_change_records_history(self):
        with closing(connect(self.database)) as db, patch('builtins.input',side_effect=['1','2','']),redirect_stdout(StringIO()):
            staff_menu(db,10,'manager')
            self.assertEqual(db.execute('SELECT status FROM Request WHERE request_id=1').fetchone()[0],'In Progress')
            self.assertEqual(db.execute('SELECT new_status FROM RequestUpdate WHERE request_id=1 ORDER BY update_id DESC').fetchone()[0],'In Progress')


if __name__=='__main__':
    unittest.main()
