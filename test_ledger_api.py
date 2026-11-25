"""Exercise the reused Roomies expense UI's complete relational contract."""
from contextlib import closing
from copy import deepcopy
from pathlib import Path
import sqlite3
import unittest

from chore_api import prepare_database
from roomies import connect
import test_chore_api


class LedgerApiTest(unittest.TestCase):
    setUp = test_chore_api.ChoreApiTest.setUp
    request = test_chore_api.ChoreApiTest.request

    def get(self, who='alex', household=1):
        status, value = self.request(who, household, path=f'/api/database/households/{household}/ledger')
        self.assertEqual(status, 200, value)
        return value

    def save(self, snapshot, change, who='alex', household=1):
        next_ledger = deepcopy(snapshot['ledger'])
        change(next_ledger)
        return self.request(who, household, 'POST', {'revision': snapshot['revision'], 'ledger': next_ledger}, path=f'/api/database/households/{household}/ledger')

    def expense(self, **extra):
        return {'id': 'new-bill', 'title': 'Roomies bill', 'category': 'Other', 'amountCents': 1000,
                'paidBy': 'name:alex', 'splitAmong': ['name:alex','name:mia','name:sam'], 'date': '2026-11-24', **extra}

    def test_add_split_and_delete_are_real_core_relations(self):
        status, snapshot = self.save(self.get(), lambda value: value['expenses'].append(self.expense()))
        self.assertEqual(status, 201, snapshot)
        with closing(connect(self.database)) as db:
            item = db.execute("SELECT expense_id FROM ExpenseDetail WHERE client_id='new-bill'").fetchone()[0]
            self.assertEqual(db.execute('SELECT amount FROM Expense WHERE expense_id=?', (item,)).fetchone()[0], 10)
            self.assertEqual(db.execute('SELECT share_amount FROM ExpenseShare WHERE expense_id=? ORDER BY user_id', (item,)).fetchall(), [(3.34,),(3.33,),(3.33,)])
        self.assertIn('new-bill', [e['id'] for e in self.get('mia')['ledger']['expenses']])
        self.assertEqual(self.save(snapshot, lambda value: value['expenses'].pop(), who='sam')[0], 403)
        self.assertEqual(self.save(snapshot, lambda value: value['expenses'].pop())[0], 201)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ExpenseShare WHERE expense_id=?',(item,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ExpenseDetail WHERE expense_id=?',(item,)).fetchone()[0],0)

    def test_payment_and_undo_and_sender_scope(self):
        payment = {'id':'payment-one','from':'name:sam','to':'name:mia','amountCents':500,'date':'2026-11-24'}
        status, result = self.save(self.get('sam'), lambda value: value['payments'].append(payment), who='sam')
        self.assertEqual(status,201,result)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT from_user_id,to_user_id,amount_cents FROM ExpensePayment').fetchall(),[(3,2,500)])
        self.assertIn(payment,self.get('mia')['ledger']['payments'])
        undo = lambda value: value.__setitem__('payments',[p for p in value['payments'] if p['id']!='payment-one'])
        self.assertEqual(self.save(result,undo,who='alex')[0],403)
        self.assertEqual(self.save(result,undo,who='mia')[0],201)
        status,result=self.save(self.get('mia'),lambda value:value['payments'].append(payment),who='mia')
        self.assertEqual(status,201,result)
        self.assertEqual(self.save(result,undo,who='sam')[0],201)
        self.assertEqual(self.save(self.get(),lambda value: value['payments'].append(payment))[0],403)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ExpensePayment').fetchone()[0],0)

    def test_recurring_bill_stop_and_cascade(self):
        bill = self.expense(recurring={},date='2026-10-31',category='Internet')
        status, result = self.save(self.get(),lambda value: value['expenses'].append(bill))
        self.assertEqual(status,201,result)
        def stop(value):
            next(e for e in value['expenses'] if e['id']=='new-bill')['recurring']={'endMonth':'2026-11'}
        status, result = self.save(result,stop)
        self.assertEqual(status,201,result)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT end_month FROM ExpenseRecurrence').fetchall(),[('2026-11',)])
        def invalid(value):
            next(e for e in value['expenses'] if e['id']=='new-bill')['recurring']={'endMonth':'2026-09'}
        self.assertEqual(self.save(result,invalid)[0],400)
        self.assertEqual(self.save(result,lambda value: value['expenses'].pop())[0],201)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ExpenseRecurrence').fetchone()[0],0)

    def test_stale_edits_do_not_overwrite_other_residents(self):
        original=self.get()
        self.assertEqual(self.save(original,lambda value:value['expenses'].append(self.expense()))[0],201)
        self.assertEqual(self.save(original,lambda value:value['expenses'].append(self.expense(id='second-bill')))[0],409)
        latest=self.get('mia')
        self.assertNotEqual(original['revision'],latest['revision'])
        self.assertEqual(len(latest['ledger']['expenses']),3)
        # A change through the original CLI-style endpoint also invalidates a revision.
        self.request('mia',1,'PATCH',{'paid':True},path='/api/database/households/1/expenses/1')
        self.assertEqual(self.save(latest,lambda value:None,who='mia')[0],409)

    def test_manual_people_are_real_members_and_cannot_be_removed_while_used(self):
        person={'id':'name:aaron','name':'Aaron','manual':True}
        status,result=self.save(self.get(),lambda value:value['members'].append(person))
        self.assertEqual(status,201,result)
        with closing(connect(self.database)) as db:
            person_id=db.execute('SELECT user_id FROM "User" WHERE name=\'Aaron\'').fetchone()[0]
            self.assertEqual(db.execute('SELECT household_id FROM HouseholdMember WHERE user_id=?',(person_id,)).fetchone()[0],1)
        bill=self.expense(splitAmong=['name:aaron','name:alex','name:mia'])
        status,result=self.save(result,lambda value:value['expenses'].append(bill))
        self.assertEqual(status,201,result)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT share_amount FROM ExpenseShare JOIN ExpenseDetail USING(expense_id) WHERE client_id=\'new-bill\' AND user_id=?',(person_id,)).fetchone()[0],3.34)
        remove=lambda value:value.__setitem__('members',[m for m in value['members'] if m['id']!='name:aaron'])
        self.assertEqual(self.save(result,remove)[0],400)
        status,result=self.save(result,lambda value:value['expenses'].pop())
        self.assertEqual(status,201,result)
        self.assertEqual(self.save(result,remove)[0],201)
        with closing(connect(self.database)) as db:
            self.assertIsNone(db.execute('SELECT 1 FROM "User" WHERE user_id=?',(person_id,)).fetchone())

    def test_household_role_and_amount_validation_are_atomic(self):
        for who in ('riley','jordan','taylor'):
            self.assertEqual(self.request(who,1,path='/api/database/households/1/ledger')[0],403)
        for extra in ({'amountCents':True},{'amountCents':-1},{'category':'Bad'},{'paidBy':'name:riley'}, {'date':'2026-02-30'},{'splitAmong':['name:riley']},{'recurring':{'endMonth':'2026-13'}}):
            def bad(value):
                value['members'].append({'id':'name:new person','name':'New Person','manual':True})
                value['expenses'].append(self.expense(**extra))
            self.assertEqual(self.save(self.get(),bad)[0],400,extra)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM "User"').fetchone()[0],8)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM Expense').fetchone()[0],3)

    def test_legacy_paid_share_projection_and_undo(self):
        snapshot=self.get()
        payment=next(p for p in snapshot['ledger']['payments'] if p['id']=='share:2:1')
        self.assertEqual(payment['amountCents'],1500)
        self.assertEqual(self.save(snapshot,lambda value:value.__setitem__('payments',[]),who='sam')[0],403)
        status,result=self.save(snapshot,lambda value:value.__setitem__('payments',[]))
        self.assertEqual(status,201,result)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT is_paid FROM ExpenseShare WHERE expense_id=2 AND user_id=1').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ExpensePayment').fetchone()[0],0)

    def test_invalid_existing_edits_and_cross_household_sql_are_rejected(self):
        def rename(value):
            value['expenses'][0]['title']='Changed without a supported operation'
        self.assertEqual(self.save(self.get(),rename)[0],400)
        with closing(connect(self.database)) as db:
            for statement,params in [
                ('INSERT INTO ExpensePayment VALUES(?,?,?,?,?,?)',('foreign',1,4,1,100,'2026-11-24')),
                ('INSERT INTO ExpensePayment VALUES(?,?,?,?,?,?)',('zero',1,2,1,0,'2026-11-24')),
                ('INSERT INTO ExpenseRecurrence VALUES(?,?)',(1,'2026-13')),
                ('INSERT INTO ExpenseRecurrence VALUES(?,?)',(1,'2026-10'))]:
                with self.assertRaises(sqlite3.IntegrityError): db.execute(statement,params)

    def test_old_database_migration_keeps_records_and_backup(self):
        old=self.database.with_name('old.sqlite3')
        root=Path(__file__).parent
        with closing(connect(old)) as db:
            db.executescript((root/'schema.sql').read_text()+'\n'+(root/'seed.sql').read_text().split('INSERT INTO ExpenseDetail')[0])
        prepare_database(old)
        backup=old.with_name('old-before-ledger.sqlite3')
        self.assertTrue(backup.exists())
        for path in (old,backup):
            with closing(connect(path)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM Expense').fetchone()[0],3)
        with closing(connect(old)) as db:
            self.assertIsNotNone(db.execute("SELECT name FROM sqlite_master WHERE name='ExpensePayment'").fetchone())
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__':
    unittest.main()
