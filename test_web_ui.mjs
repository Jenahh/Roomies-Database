// Exercise the real browser script and form handlers against a real temporary
// HTTP/SQLite server. The tiny DOM harness is not a visual browser or layout test.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFile, writeFile, mkdir, mkdtemp, unlink, rmdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const directory = await mkdtemp(path.join(tmpdir(), 'roomies-web-ui-'));
const fixtureFrontend = path.join(directory, 'dist');
await mkdir(path.join(fixtureFrontend, 'assets'), {recursive: true});
await writeFile(path.join(fixtureFrontend, 'index.html'), '<html><head></head><body>Test frontend</body></html>');
const child = spawn(process.env.PYTHON || 'python', ['-u', path.join(root, 'web_preview.py'), '--db', path.join(directory, 'preview.sqlite3'), '--port', '0', '--frontend', fixtureFrontend], {cwd: root, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']});
let output = '', serverError = '', base, lastMutation;
child.stdout.on('data', data => { output += data; });
child.stderr.on('data', data => { serverError += data; });
child.on('error', error => { serverError += error.message; });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitFor(check, label) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (check()) return;
    await delay(15);
  }
  throw new Error('Timed out: ' + label + '\n' + serverError);
}

class Element {
  constructor(dataset = {}) { this.dataset = dataset; this.handlers = new Map(); this.attributes = {}; this.value = ''; this.disabled = false; this.hidden = false; }
  addEventListener(name, callback, options = {}) { if (!this.handlers.has(name)) this.handlers.set(name, []); this.handlers.get(name).push({callback, once: options.once}); }
  async emit(name, event = {}) {
    for (const entry of [...(this.handlers.get(name) || [])]) {
      if (entry.once) this.handlers.set(name, this.handlers.get(name).filter(item => item !== entry));
      await entry.callback(event);
    }
  }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  set innerHTML(value) {
    this.html = value;
    const options = [...value.matchAll(/<option value="([^"]*)"([^>]*)>/g)];
    if (options.length) this.value = (options.find(item => /\bselected\b/.test(item[2])) || options[0])[1];
  }
  get innerHTML() { return this.html || ''; }
  closest() { return null; }
  showModal() { queueMicrotask(() => { this.returnValue = 'delete'; this.emit('close'); }); }
}

const ids = ['account', 'household', 'refresh', 'workspace', 'message', 'role-description', 'open-roomies', 'confirm-dialog', 'confirm-description', 'app-panel', 'tools-panel', 'more-panel', 'account-name', 'account-avatar', 'roomies-frame', 'app-status', 'account-settings', 'account-shortcut', 'details-shortcut', 'primary-task-label'];
const elements = Object.fromEntries(ids.map(id => ['#' + id, new Element()]));
const tabs = ['expenses', 'announcements', 'households', 'leases', 'requests'].map(feature => new Element({feature}));
const modes = ['home', 'more'].map(experience => new Element({experience}));
const appTabs = ['Chores', 'Calendar', 'Profile'].map(appTab => new Element({appTab}));
elements['#primary-task'] = appTabs[0];
elements['#details-shortcut'] = modes[1];
const frameMessages = [];
elements['#roomies-frame'].contentWindow = {postMessage(data) { frameMessages.push(data); }};
const windowHandlers = new Map();
globalThis.location = {hash: '', origin: 'http://localhost'};
globalThis.history = {pushState: (_state, _title, hash) => { location.hash = hash; }, replaceState: (_state, _title, hash) => { location.hash = hash; }};
globalThis.window = {addEventListener: (name, handler) => windowHandlers.set(name, handler)};
globalThis.document = {
  body: {dataset: {}},
  querySelector: selector => { assert.ok(elements[selector], 'Known DOM node: ' + selector); return elements[selector]; },
  querySelectorAll: selector => selector.includes('.tabs button') ? [...tabs, modes[0], ...appTabs] : selector === '[data-experience]' ? modes : selector === '[data-app-tab]' ? appTabs : selector === '.main-nav button' ? [modes[0], appTabs[0], tabs[0], ...appTabs.slice(1)] : [],
};
const stored = new Map();
globalThis.localStorage = {getItem: key => stored.get(key) ?? null, setItem: (key, value) => stored.set(key, value)};
globalThis.FormData = class { constructor(form) { this.values = form.values; } get(name) { return this.values[name] ?? null; } getAll(name) { const value = this.values[name]; return Array.isArray(value) ? value : value == null ? [] : [value]; } };
const realFetch = globalThis.fetch;
globalThis.fetch = async (url, init) => {
  const response = await realFetch(new URL(url, base), init);
  if (init?.method && init.method !== 'GET') lastMutation = {path: url, method: init.method, status: response.status, data: await response.clone().json()};
  return response;
};
const html = () => elements['#workspace'].innerHTML;
const ready = () => waitFor(() => elements['#workspace'].attributes['aria-busy'] === 'false', 'UI operation');
async function account(name) { const el = elements['#account']; el.value = name + '@example.com'; await el.emit('change', {target: el}); await ready(); }
async function feature(name) { await tabs.find(tab => tab.dataset.feature === name).emit('click'); await ready(); }
async function submit(kind, values, id) {
  const form = {dataset: {form: kind, id}, values};
  await elements['#workspace'].emit('submit', {preventDefault() {}, target: form});
  await ready();
}
async function action(dataset, selector) {
  const button = {dataset};
  const target = {closest: query => query === selector ? button : null};
  await elements['#workspace'].emit('click', {target});
  await ready();
}
async function rows(who, route, key) {
  const response = await realFetch(base + route, {headers: {'X-Roomies-Demo-Email': who+'@example.com'}});
  assert.equal(response.status, 200);
  return (await response.json())[key];
}

try {
  await waitFor(() => /Roomies preview: (http:\/\/127\.0\.0\.1:\d+)\/demo\//.test(output), 'server startup');
  base = output.match(/Roomies preview: (http:\/\/127\.0\.0\.1:\d+)/)[1];
  const model = await readFile(path.join(root, 'web', 'model.js'), 'utf8');
  const modelURL = 'data:text/javascript;base64,' + Buffer.from(model).toString('base64');
  const code = (await readFile(path.join(root, 'web', 'demo.js'), 'utf8')).replace("'./model.js'", JSON.stringify(modelURL));
  await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
  await ready();
  assert.equal(elements['#app-panel'].hidden, false);
  assert.match(elements['#roomies-frame'].src, /demo_account=alex%40example.com/);
  const firstFrame = elements['#roomies-frame'].src;
  await appTabs[0].emit('click'); await ready();
  assert.equal(location.hash, '#chores');
  assert.equal(elements['#app-panel'].hidden, false);
  assert.equal(elements['#more-panel'].hidden, true);
  assert.equal(elements['#roomies-frame'].src, firstFrame);
  assert.equal(frameMessages.at(-1).tab, 'Chores');
  assert.equal(appTabs[0].attributes['aria-current'], 'page');
  await appTabs[1].emit('click'); await ready();
  assert.equal(location.hash, '#calendar');
  assert.equal(appTabs[1].attributes['aria-current'], 'page');
  await appTabs[2].emit('click'); await ready();
  assert.equal(location.hash, '#profile');
  assert.equal(appTabs[2].attributes['aria-current'], 'page');
  console.log('PASS: Chores, Calendar and Profile are one-tap tabs without resetting the app');
  await feature('expenses');
  assert.equal(elements['#tools-panel'].hidden, false);
  assert.equal(elements['#app-panel'].hidden, true);
  assert.match(html(), /Internet bill/);
  assert.match(html(), /Groceries/);

  await submit('expense', {title: 'Web UI <bill>', amount: '10.00', date: '2026-11-24', paidById: '1', memberIds: ['1','2','3']});
  assert.equal(lastMutation.status, 201);
  const expense = lastMutation.data.expenses.find(row => row.title === 'Web UI <bill>');
  assert.match(html(), /Web UI &lt;bill&gt;/);
  assert.ok(!html().includes('Web UI <bill>'));
  await account('mia');
  assert.match(html(), /\$3\.33/);
  await action({id: expense.id, paid: 'true'}, '[data-paid]');
  assert.equal(lastMutation.status, 200);
  assert.equal((await rows('mia', '/api/database/households/1/expenses', 'expenses')).find(row => row.id===expense.id).settled, 1);
  await modes[0].emit('click'); await ready();
  assert.match(elements['#roomies-frame'].src, /demo_account=mia%40example.com/);
  const cached = JSON.parse(stored.get('roomies:resident:mia@example.com'));
  assert.equal(cached.expenses.find(row => row.id===expense.id).settled, 1);
  assert.match(cached.household, /Unit 2A/);
  await feature('expenses');
  await account('alex');
  await action({id: expense.id, delete: 'expenses', title: expense.title}, '[data-delete]');
  assert.equal(lastMutation.status, 200);
  assert.ok(!html().includes('Web UI &lt;bill&gt;'));
  console.log('PASS: Expense form, exact split, payment update, deletion and escaped text');

  await account('taylor'); await feature('announcements');
  await submit('announcement', {title: 'A shared update', body: '<script>alert(1)</script>'});
  assert.equal(lastMutation.status, 201);
  const post = lastMutation.data.announcements.find(row => row.title === 'A shared update');
  assert.match(html(), /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  await account('alex');
  assert.match(html(), /A shared update/);
  assert.ok(!html().includes(`data-delete="announcements" data-id="${post.announcement_id}"`));
  await account('jordan');
  assert.equal(elements['#primary-task-label'].textContent, 'Requests');
  await action({id: String(post.announcement_id), delete: 'announcements', title: post.title}, '[data-delete]');
  assert.equal(lastMutation.status, 200);
  console.log('PASS: Announcement posting, shared visibility, role-aware delete control');

  await feature('households');
  await submit('household', {propertyId: '1', unit: 'UI 9Z', raId: '11'});
  assert.equal(lastMutation.status, 201);
  const household = lastMutation.data.households.find(row => row.unit_label === 'UI 9Z');
  assert.match(elements['#household'].innerHTML, /UI 9Z/);
  elements['#household'].value = String(household.household_id);
  await elements['#household'].emit('change', {target: elements['#household']}); await ready();
  await feature('leases'); assert.match(html(), /This unit has no members/);
  await feature('households');
  await action({id: String(household.household_id), delete: 'households', title: 'Unit UI 9Z'}, '[data-delete]');
  assert.equal(lastMutation.status, 200);
  assert.ok(!elements['#household'].innerHTML.includes('UI 9Z'));
  await action({id: '1', delete: 'households', title: 'Unit 2A'}, '[data-delete]');
  assert.equal(lastMutation.status, 400);
  assert.match(elements['#message'].textContent, /cannot be deleted/);
  console.log('PASS: Household create/delete, selector refresh, populated-household rejection');

  await feature('leases');
  const leaseInput = {userId: '1', start: '2027-06-01', end: '2028-05-31', rent: '675.00'};
  await submit('lease', leaseInput);
  assert.equal(lastMutation.status, 201);
  const lease = lastMutation.data.leases.find(row => row.monthly_rent===675);
  await submit('lease', leaseInput);
  assert.equal(lastMutation.status, 409);
  assert.match(elements['#message'].textContent, /overlapping/);
  await account('alex'); assert.match(html(), /\$675\.00/); assert.ok(!html().includes('>Sam<'));
  await account('taylor'); assert.match(html(), /Lease details are private/);
  await account('jordan');
  await action({id: String(lease.lease_id), delete: 'leases', title: 'Alex lease'}, '[data-delete]');
  assert.equal(lastMutation.status, 200);
  console.log('PASS: Lease form, overlap error, private resident view, manager delete');

  await account('alex'); await feature('requests');
  await submit('request', {type: 'Maintenance', description: 'UI kitchen repair'});
  assert.equal(lastMutation.status, 201);
  const request = lastMutation.data.requests.find(row => row.description==='UI kitchen repair');
  await account('jordan'); assert.match(html(), /UI kitchen repair/);
  await submit('status', {status: 'In Progress', note: 'Repair scheduled'}, String(request.id));
  assert.equal(lastMutation.status, 200);
  await account('alex'); assert.match(html(), /Repair scheduled/); assert.match(html(), /View history \(1\)/);
  await account('mia');
  await submit('request', {type: 'RA Concern', description: 'UI quiet hours concern'});
  assert.equal(lastMutation.status, 201);
  const concern = lastMutation.data.requests.find(row => row.description==='UI quiet hours concern');
  await account('taylor'); assert.match(html(), /UI quiet hours concern/);
  await submit('status', {status: 'Closed', note: 'Discussed quiet hours'}, String(concern.id));
  assert.equal(lastMutation.status, 200);
  await account('mia'); assert.match(html(), /Discussed quiet hours/); assert.match(html(), />Closed</);
  console.log('PASS: Resident forms, manager and RA updates, refreshed status/history');
  await modes[1].emit('click'); await ready();
  assert.equal(elements['#more-panel'].hidden, false);
  assert.equal(elements['#tools-panel'].hidden, true);
  assert.equal(location.hash, '#details');
  await appTabs[0].emit('click'); await ready();
  assert.equal(elements['#app-panel'].hidden, false);
  assert.match(elements['#roomies-frame'].src, /demo_tab=Chores/);
  const message = windowHandlers.get('message');
  const origin = location.origin, source = elements['#roomies-frame'].contentWindow;
  message({origin: 'https://wrong.example', source, data: {type: 'roomies:feature', feature: 'expenses', email: 'mia@example.com'}});
  assert.equal(elements['#app-panel'].hidden, false);
  message({origin, source, data: {type: 'roomies:feature', feature: 'expenses', email: 'mia@example.com'}});
  await ready();
  assert.equal(elements['#tools-panel'].hidden, false);
  assert.equal(location.hash, '#expenses');
  console.log('PASS: Main app navigation, secondary Details, selected account, bill cache and origin checks');
  await import('./test_app_bridge.mjs');
  // Check native mode too: Bills opens the reused Expenses screen.
  for (const element of new Set([...Object.values(elements),...tabs,...modes,...appTabs])) element.handlers.clear();
  windowHandlers.clear(); stored.clear(); location.hash='#bills';
  const previousFetch=globalThis.fetch;
  globalThis.fetch=async (url,init)=>{
    const response=await previousFetch(url,init);
    if(url==='/api/demo/accounts') return new Response(JSON.stringify({...await response.json(),expenseLedgerAvailable:true}),{status:200,headers:{'Content-Type':'application/json'}});
    return response;
  };
  await import('data:text/javascript;base64,'+Buffer.from(code+'\n// native-ledger shell contract').toString('base64'));
  await ready();
  assert.equal(elements['#app-panel'].hidden,false);
  assert.equal(elements['#tools-panel'].hidden,true);
  assert.match(elements['#roomies-frame'].src,/demo_tab=Expenses/);
  await feature('expenses');
  assert.equal(location.hash,'#bills');
  assert.equal(frameMessages.at(-1).tab,'Expenses');
  console.log('PASS: SQL build flag routes Bills directly to the reused Roomies Expenses screen');
  console.log('All browser-script workflow checks passed. Visual browser review is still needed.');
} finally {
  const exited = new Promise(resolve => child.once('exit', resolve));
  if (child.exitCode === null) { child.kill(); await exited; }
  // Remove only the exact temporary files this test created, without recursion.
  for (const name of ['preview.sqlite3', 'preview.sqlite3-journal']) await unlink(path.join(directory, name)).catch(() => {});
  await unlink(path.join(fixtureFrontend, 'index.html')).catch(() => {});
  await rmdir(path.join(fixtureFrontend, 'assets')).catch(() => {});
  await rmdir(fixtureFrontend).catch(() => {});
  await rmdir(directory).catch(() => {});
}
