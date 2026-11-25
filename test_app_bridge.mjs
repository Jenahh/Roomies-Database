// Contract tests for the embedding adapter; no browser layout is simulated.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const source = await readFile(new URL('./web/app-bridge.js', import.meta.url), 'utf8');
const messages = [], handlers = {}, events = [];
let signedIn = false, selected = '';
const current = new URL('http://localhost/login?roomies_embed=1&demo_account=alex%40example.com&demo_tab=Chores');
const parent = {postMessage: (data, origin) => messages.push({data, origin})};
class Input {
  set value(value) { this.content = value; }
  get value() { return this.content; }
  dispatchEvent(event) { events.push({value: this.value, type: event.type}); }
}
const email = new Input(), password = new Input();
const tabs = ['Home', 'Chores', 'Expenses', 'Calendar', 'Profile'].map(label => ({getAttribute: () => label, click: () => { selected = label; }}));
const navigation = {querySelectorAll: () => tabs, querySelector: () => tabs.find(tab => tab.getAttribute() === selected)};
const login = {textContent: 'Log In', click: () => { assert.equal(email.value, 'alex@example.com'); assert.equal(password.value, '1234'); signedIn = true; }};
const document = {
  body: {}, documentElement: {dataset: {}},
  querySelector: selector => selector.includes('tablist') ? signedIn ? navigation : null : selector.includes('Email') ? email : password,
  querySelectorAll: () => [login],
  addEventListener: (name, handler) => { handlers[name] = handler; }
};
const window = {parent, fetch: async () => ({ok: true}), addEventListener: (name, handler) => { handlers[name] = handler; }, dispatchEvent() {}};
const history = {
  pushState: (_state, _title, url) => { handlers.lastURL = url; },
  replaceState: (_state, _title, url) => { handlers.lastURL = url; }
};
vm.runInNewContext(source, {window, document, location: current, history, parent, URL, URLSearchParams, Headers,
  HTMLInputElement: Input, Event: class {constructor(type) {this.type = type;}},
  MutationObserver: class {constructor(callback) {handlers.mutation = callback;} observe() {}}, setTimeout, console});
const end = Date.now() + 2000;
while (!messages.some(item => item.data.type === 'roomies:ready') && Date.now() < end) await new Promise(resolve => setTimeout(resolve, 10));
assert.ok(signedIn);
assert.equal(selected, 'Chores');
assert.equal(events.length, 2);
assert.equal(document.documentElement.dataset.roomiesEmbedded, 'true');
assert.ok(messages.some(item => item.data.type === 'roomies:ready' && item.data.email === 'alex@example.com'));
handlers.message({origin: 'https://other.example', source: parent, data: {type: 'roomies:navigate', email: 'alex@example.com', tab: 'Profile'}});
assert.equal(selected, 'Chores');
handlers.message({origin: current.origin, source: {}, data: {type: 'roomies:navigate', email: 'alex@example.com', tab: 'Profile'}});
assert.equal(selected, 'Chores');
handlers.message({origin: current.origin, source: parent, data: {type: 'roomies:navigate', email: 'alex@example.com', tab: 'Profile'}});
assert.equal(selected, 'Profile');
handlers.mutation();
assert.ok(messages.some(item => item.data.type === 'roomies:tab' && item.data.tab === 'Profile'));
history.pushState(null, '', '/home');
assert.match(handlers.lastURL, /roomies_embed=1/);
assert.match(handlers.lastURL, /demo_account=alex%40example.com/);
let prevented = false;
handlers.click({target: {closest: () => ({getAttribute: () => 'Add expense'})}, preventDefault: () => {prevented = true;}, stopImmediatePropagation() {}});
assert.ok(prevented);
assert.ok(messages.some(item => item.data.type === 'roomies:feature' && item.data.feature === 'expenses'));
await window.fetch('/api/households/1/chores', {headers: {'X-Roomies-Demo-Email': 'mia@example.com'}});
assert.ok(messages.some(item => item.data.type === 'roomies:identity' && item.data.email === 'mia@example.com'));
window.ROOMIES_DATABASE_EXPENSES = true;
prevented = false;
handlers.click({target: {closest: () => ({getAttribute: () => 'Add expense'})}, preventDefault: () => {prevented = true;}, stopImmediatePropagation() {}});
assert.equal(prevented, false);
handlers.message({origin: current.origin, source: parent, data: {type:'roomies:navigate',email:'mia@example.com',tab:'Expenses'}});
assert.equal(selected, 'Expenses');
handlers.mutation();
assert.ok(messages.some(item => item.data.type === 'roomies:tab' && item.data.tab === 'Expenses'));
console.log('PASS: Embedded login controls, app navigation, bill routing and identity messages');
