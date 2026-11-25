// Verify the original Roomies financial algorithms against real HTTP/SQLite.
// Requires the original app checkout's installed TypeScript; no source is edited.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFile,mkdtemp,unlink,rmdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const source=path.resolve(process.argv[2] || path.join(root,'..','roomies-github-current'));
const module=await import(pathToFileURL(path.join(source,'node_modules','typescript','lib','typescript.js')).href);
const ts=module.default || module;
const transpile=text=>ts.transpileModule(text,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const data=text=>'data:text/javascript;base64,'+Buffer.from(text).toString('base64');
const settlement=data(transpile(await readFile(path.join(source,'app/features/settlement/settlement.ts'),'utf8')));
const ledgerCode=transpile(await readFile(path.join(source,'app/features/settlement/ledger.ts'),'utf8')).replace(/from ['"]\.\/settlement['"]/g,'from '+JSON.stringify(settlement));
const {expenseOccurrences,memberSummaries,planSettlement}=await import(data(ledgerCode));
const directory=await mkdtemp(path.join(tmpdir(),'roomies-native-ledger-'));
const child=spawn(process.env.PYTHON || 'python',['-u',path.join(root,'web_preview.py'),'--db',path.join(directory,'test.sqlite3'),'--port','0'],{cwd:root,windowsHide:true,stdio:['ignore','pipe','pipe']});
let log='',errors='',base;
child.stdout.on('data',value=>{log+=value;});child.stderr.on('data',value=>{errors+=value;});
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function get(who='alex') {
  const response=await fetch(base+'/api/database/households/1/ledger',{headers:{'X-Roomies-Demo-Email':who+'@example.com'}});
  const result=await response.json();assert.equal(response.status,200,JSON.stringify(result));return result;
}
async function save(snapshot,change,who='alex') {
  const ledger=structuredClone(snapshot.ledger);change(ledger);
  const response=await fetch(base+'/api/database/households/1/ledger',{method:'POST',headers:{'Content-Type':'application/json','X-Roomies-Demo-Email':who+'@example.com'},body:JSON.stringify({revision:snapshot.revision,ledger})});
  const result=await response.json();assert.equal(response.status,201,JSON.stringify(result));return result;
}
try {
  const deadline=Date.now()+15000;
  while(!/Roomies preview: (http:\/\/127\.0\.0\.1:\d+)/.test(log)&&Date.now()<deadline) await pause(20);
  assert.match(log,/Roomies preview:/,errors);base=log.match(/Roomies preview: (http:\/\/127\.0\.0\.1:\d+)/)[1];
  let snapshot=await get();
  // Start from an empty ledger using each payer's authorized deletion, so the
  // settlement proof is independent of pre-existing seed debts.
  snapshot=await save(snapshot,value=>{value.expenses=value.expenses.filter(e=>e.paidBy!=='name:alex');});
  snapshot=await save(snapshot,value=>{value.expenses=[];},'mia');
  snapshot=await get();
  assert.equal(snapshot.ledger.payments.length,0);
  snapshot=await save(snapshot,value=>value.expenses.push({id:'native-monthly',title:'Internet',category:'Internet',amountCents:1000,paidBy:'name:alex',splitAmong:['name:alex','name:mia','name:sam'],date:'2026-10-31',recurring:{}}));
  const occurrences=expenseOccurrences(snapshot.ledger,'2026-12');
  assert.deepEqual(occurrences.map(e=>e.date),['2026-10-31','2026-11-30','2026-12-31']);
  const balances=memberSummaries(snapshot.ledger,'2026-12');
  assert.equal(balances.find(b=>b.id==='name:alex').balanceCents,1998);
  assert.equal(balances.find(b=>b.id==='name:mia').balanceCents,-999);
  const plan=planSettlement(snapshot.ledger,'2026-12');
  assert.equal(plan.transfers.length,2);
  for(const [index,transfer] of plan.transfers.entries()) {
    const sender=transfer.from.replace('name:','');
    snapshot=await save(snapshot,value=>value.payments.push({id:'native-payment-'+index,from:transfer.from,to:transfer.to,amountCents:transfer.cents,date:'2026-12-31'}),sender);
  }
  assert.ok(memberSummaries(snapshot.ledger,'2026-12').every(b=>b.balanceCents===0));
  assert.equal(planSettlement(snapshot.ledger,'2026-12').transfers.length,0);
  snapshot=await save(snapshot,value=>{value.payments=value.payments.filter(p=>p.id!=='native-payment-0');});
  assert.ok(planSettlement(snapshot.ledger,'2026-12').transfers.length>0);
  snapshot=await save(snapshot,value=>{value.expenses[0].recurring.endMonth='2026-11';});
  assert.equal(expenseOccurrences(snapshot.ledger,'2027-06').length,2);
  const other=await get('mia');assert.deepEqual(other.ledger,snapshot.ledger);
  console.log('PASS: Reused Roomies algorithms, monthly dates, exact splits, optimized settlement, record/undo payments and stop repeating against SQLite');
} finally {
  const exit=new Promise(resolve=>child.once('exit',resolve));if(child.exitCode===null){child.kill();await exit;}
  for(const name of ['test.sqlite3','test.sqlite3-journal']) await unlink(path.join(directory,name)).catch(()=>{});
  await rmdir(directory).catch(()=>{});
}
