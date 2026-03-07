import API_BASE_URL from '../config/api';

/**
 * Search for a stock by name/symbol using the 5paisa scripmaster route.
 * Returns full snapshot data (price, change, high, low, volume …).
 *
 * @param {string} symbol   - e.g. "TCS", "RELIANCE"
 * @param {string} exchange - "N" for NSE (default) or "B" for BSE
 */
export async function searchStockByName(symbol, exchange = 'N') {
  const url = `${API_BASE_URL}/stocks/get-stock-by-name/${encodeURIComponent(symbol)}?exchange=${exchange}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Get a live snapshot for a known scrip code.
 *
 * @param {number} scripCode
 * @param {string} exchange      - "N" or "B"
 * @param {string} exchangeType  - "C" (cash) default
 */
export async function getSnapshot(scripCode, exchange = 'N', exchangeType = 'C') {
  const url = `${API_BASE_URL}/stocks/5paisa/snapshot/${scripCode}?exchange=${exchange}&exchange_type=${exchangeType}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Search the 5paisa scripmaster for stocks matching a partial query.
 *
 * @param {string} query    - partial name, e.g. "RELI"
 * @param {string} exchange - "N" or "B"
 * @returns {Promise<{results: Array, count: number}>}
 */
export async function searchScripmaster(query, exchange = 'N') {
  const url = `${API_BASE_URL}/stocks/5paisa/search?q=${encodeURIComponent(query)}&exchange=${exchange}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}
