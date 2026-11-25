import {escapeHtml as e, money, roleName, scopesFor, localDay, recordPath} from './model.js';

const $ = selector => document.querySelector(selector);
const state = {accounts: [], account: null, households: [], properties: [], members: [], household: null,
  feature: 'expenses', scope: 'resident', data: {}, busy: false,
  experience: 'home', frontendAvailable: false, nativeExpenses: false, appEmail: null, appTab: 'Home', appDirty: true, appReady: false};
const featureNames = {expenses: 'Expenses', announcements: 'Announcements', households: 'Households', leases: 'Leases', requests: 'Requests & history'};
const appRoutes = {home: 'Home', chores: 'Chores', bills: 'Expenses', calendar: 'Calendar', profile: 'Profile', 'staff-requests': 'Requests', concerns: 'Concerns'};
const appRoute = tab => Object.keys(appRoutes).find(key => appRoutes[key] === tab) || 'home';
const accountStore = 'roomies-4402-demo-account';
let rememberEmail = 'alex@example.com';
try { rememberEmail = localStorage.getItem(accountStore) || rememberEmail; } catch { /* Private browsing can disable storage. */ }

function notice(message, error = false) {
  const box = $('#message');
  box.textContent = message;
  box.className = error ? 'notice error' : 'notice';
  box.hidden = !message;
}
function busy(value) {
  state.busy = value;
  $('#workspace').setAttribute('aria-busy', String(value));
  $('#account').disabled = value || !state.accounts.length;
  $('#household').disabled = value || !state.households.length;
  $('#refresh').disabled = value || !state.account;
  document.querySelectorAll('.tabs button, #workspace button, #workspace select, #workspace input, #workspace textarea').forEach(item => { item.disabled = value; });
}
async function api(path, method = 'GET', body) {
  const response = await fetch(path, {
    method, cache: 'no-store', headers: {'Content-Type': 'application/json', 'X-Roomies-Demo-Email': state.account?.email || ''},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'The request could not be completed.');
  return result;
}
async function run(work, success) {
  if (state.busy) return;
  notice(''); busy(true);
  try { await work(); if (success) notice(success); }
  catch (error) { notice(error.message || 'Could not connect. Keep the preview server running, then refresh.', true); }
  finally { busy(false); }
}
const isResident = () => state.members.some(member => member.user_id === state.account?.user_id);
const isManager = () => state.properties.some(property => property.property_id === state.household?.property_id);
const empty = (title, description) => `<div class="empty"><h2>${e(title)}</h2><p>${e(description)}</p></div>`;
const options = (rows, key, label, selected) => rows.map(row => `<option value="${e(row[key])}" ${row[key] === selected ? 'selected' : ''}>${e(typeof label === 'function' ? label(row) : row[label])}</option>`).join('');
const heading = (title, description, extra = '') => `<div class="section-heading"><div><h2>${e(title)}</h2><p>${e(description)}</p></div>${extra}</div>`;
const field = (label, name, type = 'text', value = '', attrs = '') => `<div class="field"><label for="${e(name)}">${e(label)}</label><input id="${e(name)}" name="${e(name)}" type="${e(type)}" value="${e(value)}" ${attrs} required></div>`;
const deleteButton = (kind, id, title) => `<button type="button" class="button small-button danger-outline" data-delete="${e(kind)}" data-id="${e(id)}" data-title="${e(title)}">Delete</button>`;
const householdLabel = row => `${row.property} · Unit ${row.unit_label}`;

function renderShell() {
  const home = state.experience === 'home';
  $('#app-panel').hidden = !home;
  $('#more-panel').hidden = state.experience !== 'more';
  $('#tools-panel').hidden = state.experience !== 'tools';
  document.body.dataset.experience = state.experience;
  $('#account-name').textContent = state.account?.name || 'Your household';
  $('#account-avatar').textContent = state.account?.name?.slice(0, 1) || 'R';
  const task = state.account?.roles.includes('resident') ? 'Chores' : state.account?.roles.includes('manager') ? 'Requests' : 'Concerns';
  $('#primary-task').dataset.appTab = task;
  $('#primary-task-label').textContent = task;
  document.querySelectorAll('.main-nav button').forEach(button => {
    if (button.dataset.feature === 'expenses') button.hidden = !state.account?.roles.includes('resident');
    const current = button.dataset.appTab
      ? home && state.appTab === button.dataset.appTab
      : button.dataset.experience
      ? home && state.appTab === 'Home'
      : button.dataset.feature === 'expenses' && state.nativeExpenses && home ? state.appTab === 'Expenses'
      : state.experience === 'tools' && button.dataset.feature === state.feature;
    if (current) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  const details = state.experience === 'more' || (state.experience === 'tools' && state.feature !== 'expenses');
  if (details) $('#details-shortcut').setAttribute('aria-current', 'page'); else $('#details-shortcut').removeAttribute('aria-current');
}
function route(name, replace = false) {
  if (location.hash !== '#' + name) history[replace ? 'replaceState' : 'pushState'](null, '', '#' + name);
}
async function showFeature(feature, remember = true) {
  if (feature === 'expenses' && state.nativeExpenses) { await showApp('Expenses', remember); return; }
  state.experience = 'tools'; state.feature = feature;
  await loadView(); renderShell();
  if (remember) route(feature);
}
async function showApp(tab = 'Home', remember = true) {
  if (!state.frontendAvailable) {
    await showFeature('expenses', remember);
    notice('Build the existing Roomies app to enable Home and the original screens. The household tools are ready.', true);
    return;
  }
  const frame = $('#roomies-frame');
  state.experience = 'home'; state.appTab = tab; renderShell();
  if (remember) route(appRoute(tab));
  if (state.appEmail !== state.account.email || state.appDirty) {
    // Refresh only the preview origin's display cache before remounting the
    // original app. SQLite is authoritative for these bill values.
    if (isResident() && !state.nativeExpenses) {
      const {expenses} = await api(recordPath(state.household.household_id, 'expenses'));
      try {
        const key = 'roomies:resident:' + state.account.email;
        let saved;
        try { saved = JSON.parse(localStorage.getItem(key) || 'null'); } catch { saved = null; }
        const valid = saved && typeof saved.name === 'string' && Array.isArray(saved.chores) && Array.isArray(saved.events) &&
          (saved.pet === null || (typeof saved.pet?.name === 'string' && (saved.pet.lastAttention === null || typeof saved.pet.lastAttention === 'string')));
        const data = valid ? saved : {name: state.account.name, pet: null, chores: [], events: []};
        localStorage.setItem(key, JSON.stringify({...data, household: householdLabel(state.household), expenses}));
      } catch { /* The app can still run if optional display caching is blocked. */ }
    }
    state.appEmail = state.account.email; state.appDirty = false; state.appReady = false;
    $('#app-status').textContent = 'Opening Roomies for ' + state.account.name + '…';
    delete $('#app-status').dataset.error;
    $('#app-status').hidden = false; frame.hidden = true;
    frame.src = '/login?' + new URLSearchParams({roomies_embed: '1', demo_account: state.account.email, demo_tab: tab});
  } else frame.contentWindow?.postMessage({type: 'roomies:navigate', email: state.account.email, tab}, location.origin);
}

async function loadContext() {
  const selected = state.household?.household_id;
  const data = await api('/api/database/households');
  state.households = data.households;
  state.properties = data.properties;
  state.household = state.households.find(h => h.household_id === selected) || state.households[0] || null;
  $('#household').innerHTML = state.households.length ? options(state.households, 'household_id', householdLabel, state.household.household_id) : '<option>No assigned households</option>';
  $('#role-description').textContent = `${state.account.name} · ${state.account.roles.map(roleName).join(', ')}. Your access follows your household and property assignments.`;
  await loadMembers();
}
async function loadMembers() {
  state.members = state.household ? (await api(recordPath(state.household.household_id, 'members'))).members : [];
}
async function loadView() {
  state.data = {};
  if (state.feature === 'requests') {
    const scopes = scopesFor(state.account);
    if (!scopes.includes(state.scope)) state.scope = scopes[0];
    if (state.scope) state.data = await api('/api/requests/' + state.scope);
  } else if (state.household && (state.feature === 'announcements' ||
      (state.feature === 'expenses' && isResident()) ||
      (state.feature === 'leases' && (isManager() || isResident())))) {
    state.data = await api(recordPath(state.household.household_id, state.feature));
  }
  render();
}
function renderExpenses() {
  if (!isResident()) return empty('Shared expenses are for residents', 'Choose Alex, Mia, Sam, or Riley to view and split bills for their household.');
  const rows = state.data.expenses || [];
  const outstanding = rows.reduce((sum, row) => sum + (row.settled ? 0 : row.amount), 0);
  return heading('Household bills', 'Split a cost and keep track of your share.') + `
    <div class="split"><details class="card sticky-form editor"><summary>Add a bill</summary><form data-form="expense"><fieldset>
      ${field('What was it for?', 'title', 'text', '', 'maxlength="2000" placeholder="e.g. Electricity bill"')}
      <div class="two-fields" style="margin-top:15px">${field('Total amount ($)', 'amount', 'number', '', 'min="0.01" step="0.01" max="10000000"')}${field('Date', 'date', 'date', localDay())}</div>
      <div class="field" style="margin-top:15px"><label for="payer">Paid by</label><select id="payer" name="paidById">${options(state.members, 'user_id', 'name', state.account.user_id)}</select></div>
      <div style="margin-top:16px"><p class="field-label">Split equally between</p><div class="checks">${state.members.map(member => `<label class="check"><input type="checkbox" name="memberIds" value="${member.user_id}" checked>${e(member.name)}</label>`).join('')}</div><p class="small" style="margin-top:8px">Any remainder cents are included so the shares equal the total.</p></div>
      <div class="form-footer"><button class="button" type="submit">Save expense</button></div>
    </fieldset></form></details><section><div class="summary">Your unpaid total: <strong>${money(outstanding)}</strong> · ${rows.length} household bills</div><div class="record-list">
    ${rows.map(row => `<article class="card"><div class="row"><div><div class="record-title">${e(row.title)}</div><div class="record-meta">Paid by ${e(row.paidBy)} · ${e(row.due)} · Bill #${e(row.id)}</div></div><span class="label ${row.settled ? 'paid' : ''}">${row.settled ? 'Settled' : 'Unpaid'}</span></div><div class="row" style="margin-top:17px"><span>Your share</span><span class="amount">${money(row.amount)}</span></div><p class="record-meta">${money(row.totalAmount)} total · ${e(row.splitCount)} people</p><div class="record-actions">${row.hasShare ? `<button type="button" class="button secondary small-button" data-paid="${row.settled ? 'false' : 'true'}" data-id="${e(row.id)}">${row.settled ? 'Mark my share unpaid' : 'Mark my share paid'}</button>` : '<span class="small">You are not included in this split.</span>'}${row.canDelete ? deleteButton('expenses', row.id, row.title) : ''}</div></article>`).join('') || empty('No shared bills yet', 'Add your first household expense with the form.')}
    </div></section></div>`;
}
function renderAnnouncements() {
  return heading('Household updates', 'A shared place for news, reminders, and announcements.') + `
    <div class="split"><details class="card sticky-form editor"><summary>Post an update</summary><form data-form="announcement"><fieldset>
      ${field('Title', 'title', 'text', '', 'maxlength="2000" placeholder="e.g. Household meeting"')}
      <div class="field"><label for="body">Message</label><textarea id="body" name="body" maxlength="2000" required placeholder="What should your household know?"></textarea></div>
      <div class="form-footer"><button class="button" type="submit">Post announcement</button></div>
    </fieldset></form></details><div class="record-list">${(state.data.announcements || []).map(row => `<article class="card"><span class="pill">Announcement #${e(row.announcement_id)}</span><h3 style="margin-top:12px">${e(row.title)}</h3><p class="record-meta">${e(row.author)} · ${e(row.posted_at)}</p><p class="record-body">${e(row.body)}</p>${row.canDelete ? `<div class="record-actions">${deleteButton('announcements', row.announcement_id, row.title)}</div>` : ''}</article>`).join('') || empty('A quiet bulletin board', 'Post an update for your household to read.')}</div></div>`;
}
function renderHouseholds() {
  const manager = state.properties.length > 0;
  const form = manager ? `<details class="card sticky-form editor"><summary>Add a household</summary><form data-form="household"><fieldset>
    <div class="field"><label for="propertyId">Property</label><select id="propertyId" name="propertyId">${options(state.properties, 'property_id', 'name', state.household?.property_id)}</select></div>
    ${field('Unit label', 'unit', 'text', '', 'maxlength="100" placeholder="e.g. 9Z"')}
    <div class="field"><label for="raId">Resident assistant (optional)</label><select id="raId" name="raId"><option value="">No RA assigned</option>${options(state.accounts.filter(account => account.roles.includes('ra')), 'user_id', 'name')}</select></div>
    <div class="form-footer"><button class="button" type="submit">Create household</button></div>
    <p class="small" style="margin-top:12px">New units start empty. Use the seeded households to try features that need resident members.</p>
  </fieldset></form></details>` : '';
  return heading('Your households', manager ? 'Manage units in your properties. Only empty households can be deleted.' : 'The households you belong to or support.') + `<div class="${manager ? 'split' : ''}">${form}<div class="record-list">${state.households.map(row => `<article class="card"><div class="row"><div><div class="record-title">Unit ${e(row.unit_label)}</div><div class="record-meta">${e(row.property)} · Household #${row.household_id}</div></div><span class="label">${row.household_id === state.household?.household_id ? 'Selected' : 'Assigned'}</span></div><p class="small" style="margin-top:15px">RA: ${e(state.accounts.find(a => a.user_id === row.ra_user_id)?.name || 'Not assigned')}</p>${state.properties.some(p => p.property_id === row.property_id) ? `<div class="record-actions">${deleteButton('households', row.household_id, 'Unit ' + row.unit_label)}</div>` : ''}</article>`).join('') || empty('No households yet', 'Create a unit in a property you manage.')}</div></div>`;
}
function renderLeases() {
  if (!(isManager() || isResident())) return empty('Lease details are private to residents and managers', 'Choose a resident to see their own lease or the assigned manager to manage household leases.');
  const manager = isManager();
  const form = manager ? `<details class="card sticky-form editor"><summary>Add a lease</summary>${state.members.length ? `<form data-form="lease"><fieldset><div class="field"><label for="userId">Resident</label><select id="userId" name="userId">${options(state.members, 'user_id', 'name')}</select></div>
    ${field('Start date', 'start', 'date', '2027-06-01')}${field('End date', 'end', 'date', '2028-05-31')}${field('Monthly rent ($)', 'rent', 'number', '', 'min="0.01" max="10000000" step="0.01"')}
    <div class="form-footer"><button class="button" type="submit">Save lease</button></div></fieldset></form>` : '<p class="small">This unit has no members. Choose a seeded household to add a lease.</p>'}</details>` : '';
  return heading(manager ? 'Household leases' : 'Your lease', manager ? 'Rental agreements for the residents of this household.' : 'Your rent and lease dates, in one place.') + `<div class="${manager ? 'split' : ''}">${form}<div class="record-list">${(state.data.leases || []).map(row => `<article class="card"><div class="row"><div><div class="record-title">${e(row.resident)}</div><div class="record-meta">Lease #${row.lease_id} · Unit ${e(state.household.unit_label)}</div></div><div class="amount">${money(row.monthly_rent)}<span class="small"> / month</span></div></div><p style="margin-top:16px">${e(row.start_date)} through ${e(row.end_date)}</p>${manager ? `<div class="record-actions">${deleteButton('leases', row.lease_id, 'Lease for ' + row.resident)}</div>` : ''}</article>`).join('') || empty('No leases to show', manager ? 'Add a lease for an existing household member.' : 'Your assigned property manager manages your lease.')}</div></div>`;
}
function renderRequests() {
  const scopes = scopesFor(state.account);
  const extra = scopes.length > 1 ? `<div class="field queue-select"><label for="queue-scope">Queue</label><select id="queue-scope">${scopes.map(scope => `<option value="${scope}" ${scope === state.scope ? 'selected' : ''}>${e(roleName(scope))}</option>`).join('')}</select></div>` : '';
  const resident = state.scope === 'resident';
  const form = resident && isResident() ? `<details class="card sticky-form editor"><summary>Send a request</summary><form data-form="request"><fieldset><div class="field"><label for="type">Request type</label><select id="type" name="type"><option>Maintenance</option>${state.household.ra_user_id ? '<option>RA Concern</option>' : ''}</select></div><div class="field"><label for="description">Description</label><textarea id="description" name="description" required maxlength="2000" placeholder="Describe the issue and where it is."></textarea></div><div class="form-footer"><button class="button" type="submit">Submit request</button></div></fieldset></form></details>` : '';
  return heading(resident ? 'Your requests' : 'Resident requests', resident ? 'Maintenance, RA concerns, and the latest updates.' : 'Review requests from residents in your assignments.', extra) + `<div class="${form ? 'split' : ''}">${form}<div class="record-list">${(state.data.requests || []).map(row => `<article class="card"><div class="row"><span class="pill">${e(row.type)} · #${e(row.id)}</span><span class="label ${row.status === 'Closed' ? 'closed' : row.status === 'Open' ? 'open' : ''}">${e(row.status)}</span></div><h3 style="margin-top:15px">${e(row.description)}</h3><p class="record-meta">${e(row.resident)} · ${e(row.property)} · Unit ${e(row.unit)}</p>${resident ? '' : `<form data-form="status" data-id="${row.id}" class="request-form"><fieldset><div class="two-fields"><div class="field"><label for="status-${row.id}">Status</label><select id="status-${row.id}" name="status">${['Open', 'In Progress', 'Closed'].map(status => `<option ${row.status === status ? 'selected' : ''}>${status}</option>`).join('')}</select></div><div class="field"><label for="note-${row.id}">Note (optional)</label><input id="note-${row.id}" name="note" maxlength="2000" placeholder="e.g. Repair scheduled"></div></div><button class="button secondary small-button" type="submit" style="margin-top:12px">Save status</button></fieldset></form>`}<details><summary>View history (${row.history.length})</summary>${row.history.length ? `<ol class="history">${row.history.map(update => `<li><strong>${e(update.new_status)}</strong> <span class="small">by ${e(update.author)}</span><p class="small">${e(update.updated_at)}</p>${update.note ? `<p>${e(update.note)}</p>` : ''}</li>`).join('')}</ol>` : '<p class="small" style="margin-top:10px">No staff status changes have been recorded.</p>'}</details></article>`).join('') || empty('No requests in this queue', resident ? 'Submit a maintenance issue or concern for your assigned RA.' : 'New requests from your assigned residents will appear here.')}</div></div>`;
}
function render() {
  renderShell();
  document.querySelectorAll('.tabs button').forEach(button => {
    if (!button.dataset.feature || button.closest('.main-nav')) return;
    if (state.experience === 'tools' && button.dataset.feature === state.feature) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  if (!state.account) { $('#workspace').innerHTML = empty('No demo accounts available', 'Initialize the demonstration database before continuing.'); return; }
  if (!state.household && !['households', 'requests'].includes(state.feature)) {
    $('#workspace').innerHTML = empty('Choose an assigned household', state.properties.length ? 'Open Households to create a unit, or select another demo account.' : 'This account has no assigned household. Try another demo account.'); return;
  }
  $('#workspace').innerHTML = ({expenses: renderExpenses, announcements: renderAnnouncements, households: renderHouseholds, leases: renderLeases, requests: renderRequests}[state.feature])();
  document.querySelectorAll('#workspace details.editor').forEach(editor => { editor.open = !!window.matchMedia?.('(min-width: 681px)').matches; });
}

async function confirmDeletion(description) {
  const dialog = $('#confirm-dialog');
  $('#confirm-description').textContent = `Delete ${description}? This removes the saved record. Bills also lose their expense shares. Households with related records cannot be deleted.`;
  dialog.returnValue = 'cancel';
  return new Promise(resolve => { dialog.addEventListener('close', () => resolve(dialog.returnValue === 'delete'), {once: true}); dialog.showModal(); });
}
$('#workspace').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.target;
  const values = new FormData(form); // Capture before controls are disabled.
  const get = name => values.get(name);
  let path, payload, message;
  const household = state.household?.household_id;
  switch (form.dataset.form) {
    case 'expense':
      path = recordPath(household, 'expenses');
      payload = {title: get('title'), amount: get('amount'), date: get('date'), paidById: Number(get('paidById')), memberIds: values.getAll('memberIds').map(Number)};
      if (!payload.memberIds.length) { notice('Choose at least one household member for the split.', true); return; }
      message = 'Expense saved. Other household residents can refresh to see their shares.'; break;
    case 'announcement': path = recordPath(household, 'announcements'); payload = {title: get('title'), body: get('body')}; message = 'Announcement posted for this household.'; break;
    case 'household': path = '/api/database/households'; payload = {propertyId: Number(get('propertyId')), unit: get('unit'), raId: get('raId') ? Number(get('raId')) : null}; message = 'Household created. It is now available in the household selector.'; break;
    case 'lease': path = recordPath(household, 'leases'); payload = {userId: Number(get('userId')), start: get('start'), end: get('end'), rent: get('rent')}; message = 'Lease saved. The resident can view it using their demo account.'; break;
    case 'request': path = '/api/requests/resident'; payload = {householdId: household, type: get('type'), description: get('description')}; message = 'Request submitted. The assigned staff member can now review it.'; break;
    case 'status': path = '/api/requests/' + state.scope + '/' + form.dataset.id; payload = {status: get('status'), note: get('note') || 'Status updated through database demo'}; message = 'Status saved. A change to the status adds a history entry; choosing the same status adds no duplicate.'; break;
    default: return;
  }
  run(async () => {
    await api(path, form.dataset.form === 'status' ? 'PATCH' : 'POST', payload);
    state.appDirty = true;
    if (form.dataset.form === 'household') await loadContext();
    await loadView();
  }, message);
});
$('#workspace').addEventListener('click', async event => {
  const remove = event.target.closest('[data-delete]');
  const paid = event.target.closest('[data-paid]');
  if (state.busy || (!remove && !paid)) return;
  if (remove) {
    const context = {account: state.account.email, household: state.household?.household_id, feature: state.feature};
    if (!(await confirmDeletion(remove.dataset.title))) return;
    if (state.busy || context.account !== state.account.email || context.household !== state.household?.household_id || context.feature !== state.feature) return;
    run(async () => {
      const path = remove.dataset.delete === 'households' ? '/api/database/households/' + remove.dataset.id : recordPath(state.household.household_id, remove.dataset.delete, remove.dataset.id);
      await api(path, 'DELETE');
      state.appDirty = true;
      if (remove.dataset.delete === 'households') await loadContext();
      await loadView();
    }, 'Record deleted. Refreshing will keep it removed.');
  } else {
    run(async () => { await api(recordPath(state.household.household_id, 'expenses', paid.dataset.id), 'PATCH', {paid: paid.dataset.paid === 'true'}); state.appDirty = true; await loadView(); }, 'Your payment status has been saved.');
  }
});
$('#workspace').addEventListener('change', event => {
  if (event.target.id === 'queue-scope') run(async () => { state.scope = event.target.value; await loadView(); });
});
$('#account').addEventListener('change', event => run(async () => {
  state.account = state.accounts.find(account => account.email === event.target.value);
  try { localStorage.setItem(accountStore, state.account.email); } catch { /* Optional persistence only. */ }
  state.household = null;
  state.appDirty = true;
  state.scope = scopesFor(state.account)[0];
  if (state.feature === 'expenses' && !state.account.roles.includes('resident')) state.feature = 'requests';
  await loadContext(); await loadView();
  if (state.experience === 'home') await showApp('Home', false);
}));
$('#household').addEventListener('change', event => run(async () => {
  state.household = state.households.find(h => h.household_id === Number(event.target.value));
  state.appDirty = true;
  await loadMembers(); await loadView();
  if (state.experience === 'home') await showApp('Home', false);
}));
$('#refresh').addEventListener('click', () => run(async () => {
  await loadContext(); await loadView(); state.appDirty = true;
  if (state.experience === 'home') await showApp(state.appTab, false);
}, 'Showing the latest saved records.'));
document.querySelectorAll('.tabs button').forEach(button => {
  if (button.dataset.feature) button.addEventListener('click', () => run(() => showFeature(button.dataset.feature)));
});
document.querySelectorAll('[data-experience]').forEach(button => button.addEventListener('click', () => run(async () => {
  if (button.dataset.experience === 'home') await showApp();
  else { state.experience = 'more'; renderShell(); route('details'); }
})));
document.querySelectorAll('[data-app-tab]').forEach(button => button.addEventListener('click', () => run(() => showApp(button.dataset.appTab))));
$('#open-roomies').addEventListener('click', event => { event.preventDefault(); run(() => showApp()); });
$('#account-shortcut').addEventListener('click', event => { event.preventDefault(); $('#account-settings').open = !$('#account-settings').open; });
window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== $('#roomies-frame').contentWindow) return;
  if (event.data?.type === 'roomies:identity') {
    const account = state.accounts.find(item => item.email === event.data.email);
    if (account && account.email !== state.account?.email) run(async () => {
      state.account = account; state.appEmail = account.email; state.appDirty = false;
      state.household = null; state.scope = scopesFor(account)[0]; $('#account').value = account.email;
      try { localStorage.setItem(accountStore, account.email); } catch { /* Optional. */ }
      await loadContext(); await loadView();
    });
    return;
  }
  if (event.data?.email !== state.account?.email) return;
  if (event.data.type === 'roomies:ready') {
    state.appReady = true;
    $('#roomies-frame').hidden = false; $('#app-status').hidden = true;
    $('#roomies-frame').contentWindow.postMessage({type: 'roomies:navigate', email: state.account.email, tab: state.appTab}, location.origin);
  }
  if (event.data.type === 'roomies:tab' && state.appReady && state.experience === 'home' && Object.values(appRoutes).includes(event.data.tab)) {
    state.appTab = event.data.tab; renderShell(); route(appRoute(state.appTab), true);
  }
  if (event.data.type === 'roomies:error') { $('#roomies-frame').hidden = false; $('#app-status').dataset.error = 'true'; $('#app-status').textContent = event.data.message; $('#app-status').hidden = false; }
  if (event.data.type === 'roomies:feature' && event.data.feature === 'expenses') run(() => showFeature('expenses'));
});
window.addEventListener('popstate', () => run(async () => {
  const view = location.hash.slice(1);
  if (view in featureNames) await showFeature(view, false);
  else if (view === 'more' || view === 'details') { state.experience = 'more'; renderShell(); }
  else if (view in appRoutes) await showApp(appRoutes[view], false);
  else await showApp('Home', false);
}));

run(async () => {
  const result = await api('/api/demo/accounts');
  state.accounts = result.accounts;
  state.frontendAvailable = result.roomiesAvailable;
  state.nativeExpenses = result.expenseLedgerAvailable === true;
  state.account = state.accounts.find(account => account.email === rememberEmail) || state.accounts[0];
  $('#account').innerHTML = options(state.accounts, 'email', account => `${account.name} · ${account.roles.map(roleName).join(', ')}`, state.account?.email);
  if (!result.roomiesAvailable) {
    state.experience = 'tools';
    notice('The database demo is ready. Build the existing Roomies app to enable its separate interface.', true);
  }
  if (state.account) { state.scope = scopesFor(state.account)[0]; if (!state.account.roles.includes('resident')) state.feature = 'requests'; await loadContext(); }
  render();
  if (state.account) await loadView();
  const view = location.hash.slice(1);
  if (view in featureNames) await showFeature(view, false);
  else if (view === 'more' || view === 'details') { state.experience = 'more'; renderShell(); }
  else if (view in appRoutes && state.account) await showApp(appRoutes[view], false);
  else if (state.account && state.frontendAvailable) await showApp('Home', false);
});
