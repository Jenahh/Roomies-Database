// Small shared helpers: browser rendering never treats database text as HTML.
export const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));
export const money = value => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(Number(value));
export const roleName = role => ({resident: 'Resident', manager: 'Property manager', ra: 'Resident assistant'}[role] || role);
export const scopesFor = account => (account?.roles || []).filter(role => ['resident', 'manager', 'ra'].includes(role));
export function localDay() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}
export const recordPath = (household, feature, item) => `/api/database/households/${household}/${feature}${item == null ? '' : '/' + item}`;
