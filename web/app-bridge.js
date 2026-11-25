// Adapter for the unchanged compiled app, served only in the 4402 wrapper.
// Uses existing accessible controls, not React internals. Every SQL write
// continues to use the database server's role and household checks.
(() => {
  if (window.parent === window || new URLSearchParams(location.search).get('roomies_embed') !== '1') return;
  document.documentElement.dataset.roomiesEmbedded = 'true';
  const params = new URLSearchParams(location.search);
  let email = params.get('demo_account');
  const tab = params.get('demo_tab') || 'Home';
  const seeded = /^(alex|mia|sam|riley|jordan|morgan|taylor|casey)@example\.com$/;
  if (!email || !seeded.test(email)) return;
  const send = (type, data = {}) => parent.postMessage({type, email, ...data}, location.origin);
  let ready = false;
  const pause = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
  async function until(find) {
    const end = Date.now() + 12000;
    while (Date.now() < end) { const result = find(); if (result) return result; await pause(40); }
    throw new Error('The Roomies screen is still loading. Sign in with the selected demo email and password 1234.');
  }
  const navigation = () => document.querySelector('[role="tablist"][aria-label="Main navigation"]');
  const buttons = () => [...document.querySelectorAll('[role="button"],button')];
  const originalFetch = window.fetch.bind(window);
  window.fetch = (url, options) => {
    const target = new URL(typeof url === 'string' ? url : url.url, location.href);
    const identity = new Headers(options?.headers || (typeof url === 'object' ? url.headers : undefined)).get('X-Roomies-Demo-Email');
    if (target.origin === location.origin && target.pathname.startsWith('/api/') && seeded.test(identity || '') && identity !== email) {
      email = identity; send('roomies:identity');
    }
    return originalFetch(url, options);
  };
  function navigate(label) {
    const button = [...(navigation()?.querySelectorAll('[role="tab"]') || [])].find(item => item.getAttribute('aria-label') === label);
    if (button) button.click();
  }
  for (const name of ['pushState', 'replaceState']) {
    const original = history[name].bind(history);
    history[name] = (state, title, url) => {
      if (url != null) {
        const next = new URL(url, location.href);
        if (next.origin === location.origin) {
          next.searchParams.set('roomies_embed', '1');
          next.searchParams.set('demo_account', email);
          url = next.pathname + next.search + next.hash;
        }
      }
      return original(state, title, url);
    };
  }
  document.addEventListener('click', event => {
    const control = event.target.closest('[role="tab"],[role="button"],button');
    if (!control) return;
    const label = (control.getAttribute('aria-label') || control.textContent || '').trim();
    if (!window.ROOMIES_DATABASE_EXPENSES && ['Expenses', 'Add expense', 'Add your expense share'].includes(label)) {
      event.preventDefault(); event.stopImmediatePropagation();
      send('roomies:feature', {feature: 'expenses'});
    }
  }, true);
  let lastTab = '';
  const observer = new MutationObserver(() => {
    const nav = navigation();
    if (nav?.parentElement) {
      nav.parentElement.dataset.roomiesDashboard = 'true';
      const scroll = nav.parentElement.firstElementChild;
      if (scroll && scroll !== nav) scroll.dataset.roomiesScroll = 'true';
    }
    const selected = nav?.querySelector('[role="tab"][aria-selected="true"]');
    const label = selected?.getAttribute('aria-label');
    if (label === 'Expenses' && !window.ROOMIES_DATABASE_EXPENSES) {
      navigate('Home'); send('roomies:feature', {feature: 'expenses'});
    } else if (label && label !== lastTab) {
      lastTab = label; send('roomies:tab', {tab: label});
    }
  });
  observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['aria-selected']});
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== parent || event.data?.type !== 'roomies:navigate' || event.data.email !== email || !ready) return;
    if (event.data.tab === 'Refresh') buttons().find(button => button.textContent.trim() === 'Refresh')?.click();
    else if (['Home','Chores','Calendar','Profile','Requests','Concerns','Expenses'].includes(event.data.tab)) {
      navigate(event.data.tab);
      window.dispatchEvent(new Event('roomies:refresh-ledger'));
    }
  });
  (async () => {
    try {
      const input = await until(() => document.querySelector('input[aria-label="Email"]'));
      const password = document.querySelector('input[aria-label="Password"]');
      const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      set.call(input, email); input.dispatchEvent(new Event('input', {bubbles: true}));
      set.call(password, '1234'); password.dispatchEvent(new Event('input', {bubbles: true}));
      await pause(60);
      const login = buttons().find(button => button.textContent.trim() === 'Log In');
      if (!login) throw new Error('Use the Roomies login screen to continue.');
      login.click();
      await until(navigation);
      ready = true;
      navigate(tab);
      send('roomies:ready');
    } catch (error) { send('roomies:error', {message: error.message}); }
  })();
})();
