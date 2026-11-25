// Replaces only the ledger hook in the isolated CSC4402 build. The existing
// ExpensesScreen and settlement algorithms are imported from the original app.
import {useCallback, useEffect, useRef, useState} from 'react';
import {emptyLedger, type HouseholdLedger, type LedgerMember} from '../features/settlement/ledger';

type Snapshot = {ledger: HouseholdLedger; revision: string};
type Identity = {email: string; householdId?: number};
export function householdLedgerKey(household: string) {
  return 'roomies:household-expenses:' + household.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
export function useHouseholdLedger(_household: string, _roster: LedgerMember[], identity?: Identity) {
  const [ledger, setLedger] = useState<HouseholdLedger>(emptyLedger);
  const [storageError, setStorageError] = useState('');
  const current = useRef<Snapshot | null>(null);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const pending = useRef(0);
  const alive = useRef(false);
  const generation = useRef(0);
  const endpoint = identity?.householdId ? '/api/database/households/' + identity.householdId + '/ledger' : null;
  const email = identity?.email;
  const request = useCallback(async (method = 'GET', body?: object): Promise<Snapshot> => {
    if (!endpoint || !email) throw new Error('Select a seeded resident demo account to use shared expenses.');
    const response = await fetch(endpoint, {method, cache: 'no-store', headers: {'Content-Type': 'application/json', 'X-Roomies-Demo-Email': email}, ...(body ? {body: JSON.stringify(body)} : {})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Expenses could not be saved.');
    return result as Snapshot;
  }, [endpoint, email]);
  const show = useCallback((snapshot: Snapshot) => {
    if (!alive.current) return;
    current.current = snapshot; setLedger(snapshot.ledger);
  }, []);
  const load = useCallback(async () => {
    if (pending.current) return;
    const ticket = ++generation.current;
    try {
      const snapshot = await request();
      if (ticket === generation.current && !pending.current) { show(snapshot); if (alive.current) setStorageError(''); }
    } catch (error) { if (alive.current && ticket === generation.current) setStorageError((error as Error).message); }
  }, [request, show]);
  useEffect(() => {
    alive.current = true; current.current = null; setLedger(emptyLedger);
    void load();
    const refresh = () => { if (document.visibilityState !== 'hidden') void load(); };
    window.addEventListener('focus', refresh);
    window.addEventListener('roomies:refresh-ledger', refresh);
    document.addEventListener('visibilitychange', refresh);
    const timer = window.setInterval(refresh, 15000);
    return () => { alive.current = false; ++generation.current; window.clearInterval(timer); window.removeEventListener('focus', refresh); window.removeEventListener('roomies:refresh-ledger', refresh); document.removeEventListener('visibilitychange', refresh); };
  }, [load]);
  const update = useCallback((change: (value: HouseholdLedger) => HouseholdLedger) => {
    ++pending.current; ++generation.current;
    queue.current = queue.current.then(async () => {
      try {
        const base = current.current || await request();
        const snapshot = await request('POST', {revision: base.revision, ledger: change(base.ledger)});
        show(snapshot); if (alive.current) setStorageError('');
      } catch (error) {
        // Reload committed rows after a rejected/stale write. Browser-local
        // storage never substitutes for a failed database transaction.
        try { show(await request()); } catch { /* Keep the last committed snapshot. */ }
        if (alive.current) setStorageError((error as Error).message);
      } finally { --pending.current; }
    });
  }, [request, show]);
  return {ledger, update, storageError};
}
