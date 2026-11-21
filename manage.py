"""Role-scoped CLI for expenses, announcements, households, leases and history."""
import argparse
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3
from expanded_api import handle_expanded
from request_api import handle_requests, RequestError
from roomies import connect, DEFAULT_DB


def show(result):
    columns={'expenses':['id','title','totalAmount','amount','paidBy','settled'], 'leases':['lease_id','resident','start_date','end_date','monthly_rent'], 'announcements':['announcement_id','author','title','body'], 'households':['household_id','property','unit_label','ra_user_id']}
    for label, rows in result.items():
        if label in columns:
            rows=[{k:row[k] for k in columns[label]} for row in rows]
        print('\n' + label)
        if not rows:
            print('(none)')
        elif isinstance(rows,list):
            print(' | '.join(rows[0].keys()))
            for row in rows:
                print(' | '.join(str(v) for v in row.values()))
        else:
            print(rows)


def play(db):
    email = input('Demo email (e.g. alex@example.com or jordan@example.com): ').strip()
    def run(method,path,payload=None):
        with db:
            if method != 'GET':
                db.execute('BEGIN IMMEDIATE')
            result=handle_expanded(db,method,path,email,payload or {})
        show(result)
        return result
    run('GET','/api/database/households')
    while True:
        print('\n1 Households/properties  2 Add household (manager)  3 Delete EMPTY household (manager)')
        print('4 Expenses  5 Announcements  6 Leases  7 Request history  Enter Quit')
        option=input('Choose: ').strip()
        if not option:
            return
        try:
            if option=='1':
                run('GET','/api/database/households');continue
            if option=='2':
                prop=int(input('Property ID: '));unit=input('New unit label: ');ra=input('RA ID (optional): ').strip()
                run('POST','/api/database/households',{'propertyId':prop,'unit':unit,'raId':int(ra) if ra else None});continue
            if option=='7':
                scope=input('Your role (resident, manager, ra): ').strip()
                if scope not in ('resident','manager','ra'):
                    raise ValueError('Choose a listed role.')
                result=handle_requests(db,'GET',scope,None,email,{})
                for row in result['requests']:
                    print('\nRequest',row['id'],row['description'],'current status:',row['status'])
                    show({'history':row['history']})
                continue
            household=int(input('Household ID: '));base=f'/api/database/households/{household}'
            if option=='3':
                if input('Type DELETE to remove this empty household: ')=='DELETE':
                    run('DELETE',base)
                continue
            kind={'4':'expenses','5':'announcements','6':'leases'}.get(option)
            if kind is None:
                raise ValueError('Choose a listed option.')
            run('GET',base+'/'+kind)
            action=input('Enter View only | a Add | d Delete'+(' | p Mark your share paid/unpaid' if kind=='expenses' else '')+': ').strip()
            if not action:
                continue
            if action=='d':
                run('DELETE',base+'/'+kind+'/'+str(int(input('Record ID: '))));continue
            if action=='p' and kind=='expenses':
                item=int(input('Expense ID: '));paid=input('Paid? (y/n): ').strip()
                if paid not in ('y','n'):
                    raise ValueError('Choose y or n.')
                run('PATCH',base+'/expenses/'+str(item),{'paid':paid=='y'});continue
            if action!='a':
                raise ValueError('Choose a listed action.')
            if kind=='expenses':
                run('GET',base+'/members')
                title=input('Expense description: ');amount=input('Total USD (e.g. 60.00): ')
                when=input('Expense date YYYY-MM-DD (Enter today): ').strip() or date.today().isoformat()
                ids=input('Resident IDs to split between, comma-separated (Enter all members): ').strip()
                payer=input('Payer ID (Enter yourself): ').strip()
                payload={'title':title,'amount':amount,'date':when}
                if ids:
                    payload['memberIds']=[int(i.strip()) for i in ids.split(',')]
                if payer:
                    payload['paidById']=int(payer)
            elif kind=='announcements':
                payload={'title':input('Title: '),'body':input('Message: ')}
            else:
                run('GET',base+'/members')
                payload={'userId':int(input('Resident ID: ')),'start':input('Start YYYY-MM-DD: '),'end':input('End YYYY-MM-DD: '),'rent':input('Monthly rent USD: ')}
            run('POST',base+'/'+kind,payload)
        except (RequestError,ValueError,TypeError,sqlite3.IntegrityError) as error:
            print('Not saved:',error)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=DEFAULT_DB)
    args=parser.parse_args()
    if not args.db.is_file():
        parser.error('Database missing. Run python roomies.py init --db <new-file> first.')
    try:
        with closing(connect(args.db)) as db:
            db.row_factory=sqlite3.Row
            play(db)
    except (RequestError,sqlite3.Error,ValueError) as error:
        print('Unable to open demo:',error)
    except (EOFError,KeyboardInterrupt):
        print()


if __name__=='__main__':
    main()
