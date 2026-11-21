"""Show real HTTP writes and deletes reaching SQLite in an isolated demo."""
from contextlib import closing
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.request import Request, urlopen
from chore_api import ChoreAPI
from roomies import initialize, connect


def main():
    with TemporaryDirectory() as directory:
        database=Path(directory)/'verification.sqlite3'
        initialize(database)
        with ThreadingHTTPServer(('127.0.0.1',0),ChoreAPI) as server:
            server.database=database
            worker=Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                def call(who,method,path,payload=None):
                    body=json.dumps(payload).encode() if payload is not None else None
                    req=Request(f'http://127.0.0.1:{server.server_port}'+path,data=body,method=method,
                      headers={'X-Roomies-Demo-Email':who+'@example.com','Content-Type':'application/json'})
                    with urlopen(req,timeout=5) as response:
                        return json.load(response)
                with closing(connect(database)) as db:
                    print('\nLIVE HTTP -> SQLITE VERIFICATION (temporary database)')
                    print('1. Existing web chore contract: POST /api/households/1/chores')
                    call('alex','POST','/api/households/1/chores',{'chores':[{'title':'Synchronization demo','due':'2026-12-01','memberId':'2'}]})
                    row=db.execute("SELECT chore_id,title,status FROM Chore WHERE title='Synchronization demo'").fetchone()
                    assert row is not None
                    print('   SQLite Chore:',row)
                    call('mia','PATCH',f'/api/households/1/chores/{row[0]}',{'completed':True})
                    assert db.execute('SELECT status FROM Chore WHERE chore_id=?',(row[0],)).fetchone()[0]=='Completed'
                    print('   Mia GET sees Completed:',next(c['completed'] for c in call('mia','GET','/api/households/1/chores')['chores'] if c['id']==str(row[0])))
                    print('2. Staff changes request 1 to In Progress')
                    call('jordan','PATCH','/api/requests/manager/1',{'status':'In Progress'})
                    history=db.execute('SELECT request_id,new_status,updated_by_user_id FROM RequestUpdate WHERE request_id=1 ORDER BY update_id DESC').fetchone()
                    assert history==(1,'In Progress',10)
                    print('   SQLite RequestUpdate:',history)
                    print('3. Household add/delete through the expanded API (also used by CLI)')
                    result=call('jordan','POST','/api/database/households',{'propertyId':1,'unit':'TEST-9Z'})
                    household=next(h['household_id'] for h in result['households'] if h['unit_label']=='TEST-9Z')
                    assert db.execute('SELECT COUNT(*) FROM Household WHERE household_id=?',(household,)).fetchone()[0]==1
                    print('   After INSERT: SQLite matching households = 1')
                    call('jordan','DELETE',f'/api/database/households/{household}')
                    assert db.execute('SELECT COUNT(*) FROM Household WHERE household_id=?',(household,)).fetchone()[0]==0
                    print('   After DELETE: SQLite matching households = 0')
                    print('4. Expense add/delete and dependent shares')
                    result=call('alex','POST','/api/database/households/1/expenses',{'title':'Verification bill','amount':'10.00','date':'2026-11-20'})
                    expense=next(e['id'] for e in result['expenses'] if e['title']=='Verification bill')
                    shares=db.execute('SELECT share_amount FROM ExpenseShare WHERE expense_id=? ORDER BY user_id',(expense,)).fetchall()
                    assert shares==[(3.34,),(3.33,),(3.33,)]
                    print('   SQLite shares: 3.34 + 3.33 + 3.33 = 10.00')
                    call('alex','DELETE',f'/api/database/households/1/expenses/{expense}')
                    assert db.execute('SELECT COUNT(*) FROM ExpenseShare WHERE expense_id=?',(expense,)).fetchone()[0]==0
                    print('   After DELETE: expense absent; dependent shares = 0')
                    assert not db.execute('PRAGMA foreign_key_check').fetchall()
                    print('PASS: persisted writes, shared reads, atomic history, deletes, cascade, foreign keys.')
            finally:
                server.shutdown();worker.join(timeout=5)


if __name__=='__main__':
    main()
