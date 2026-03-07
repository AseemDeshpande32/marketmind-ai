/**
 * 5paisa Stock Service - Integration with 5paisa Market Data API
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

/**
 * Search for stock by name and get scrip code
 * @param {string} symbol - Stock symbol (e.g., "RELIANCE")
 * @param {string} exchange - Exchange code (N=NSE, B=BSE, default: N)
 * @returns {Promise<Object>} Stock data with scrip code
 */
export const searchStockByName = async (symbol, exchange = 'N') => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/stocks/get-stock-by-name/${symbol}?exchange=${exchange}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || data.error || 'Failed to fetch stock data');
    }

    return data;
  } catch (error) {
    console.error('Error searching stock:', error);
    throw error;
  }
};

/**
 * Get market snapshot from 5paisa API
 * @param {number} scripCode - Stock scrip code (e.g., 1660 for Reliance)
 * @param {string} exchange - Exchange code (N=NSE, B=BSE, default: N)
 * @param {string} exchangeType - Exchange type (C=Cash, D=Derivative, default: C)
 * @returns {Promise<Object>} Stock snapshot data
 */
export const get5paisaSnapshot = async (scripCode, exchange = 'N', exchangeType = 'C') => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/stocks/5paisa/snapshot/${scripCode}?exchange=${exchange}&exchange_type=${exchangeType}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || data.error || 'Failed to fetch 5paisa stock data');
    }

    return data;
  } catch (error) {
    console.error('Error fetching 5paisa snapshot:', error);
    throw error;
  }
};

/**
 * Search the 5paisa scripmaster for stocks matching a partial query.
 * @param {string} query - partial name, e.g. "RELI"
 * @param {string} exchange - "N" or "B"
 * @returns {Promise<{results: Array, count: number}>}
 */
export const searchScripmaster = async (query, exchange = 'N') => {
  try {
    const url = `${API_BASE_URL}/stocks/5paisa/search?q=${encodeURIComponent(query)}&exchange=${exchange}`;
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || err.error || `HTTP ${res.status}`);
    }
    return res.json();
  } catch (error) {
    console.error('Error searching scripmaster:', error);
    throw error;
  }
};

/**
 * Search for scrip codes by symbol name
 * @param {string} symbol - Stock symbol to search
 * @param {string} exchange - Exchange code (default: N)
 * @returns {Promise<Array>} Array of matching stocks
 */
export const searchScripCode = async (symbol, exchange = 'N') => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/stocks/search-scripcode?symbol=${symbol}&exchange=${exchange}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const data = await response.json();

    if (!response.ok && response.status !== 404) {
      throw new Error(data.message || 'Failed to search stock');
    }

    return data.results || [];
  } catch (error) {
    console.error('Error searching scrip code:', error);
    return [];
  }
};

/**
 * Common scrip codes for popular Indian stocks (fallback)
 */
export const SCRIP_CODES = {
  RELIANCE: 1660,
  TCS: 11536,
  INFY: 1594,
  HDFC: 1330,
  ICICI: 4963,
  ITC: 1660,
  SBIN: 3045,
  HINDUNILVR: 1394,
  BHARTIARTL: 10604,
  KOTAKBANK: 1922,
};

/**
 * Get scrip code by symbol name (uses API, fallback to hardcoded)
 * @param {string} symbol - Stock symbol (e.g., 'RELIANCE')
 * @returns {Promise<number|null>} Scrip code or null if not found
 */
export const getScripCode = async (symbol) => {
  try {
    // Try API search first
    const results = await searchScripCode(symbol);
    if (results && results.length > 0) {
      return results[0].scripCode;
    }
    
    // Fallback to hardcoded mapping
    const upperSymbol = symbol.toUpperCase().replace('.NS', '').replace('.BO', '');
    return SCRIP_CODES[upperSymbol] || null;
  } catch (error) {
    // If API fails, use hardcoded fallback
    const upperSymbol = symbol.toUpperCase().replace('.NS', '').replace('.BO', '');
    return SCRIP_CODES[upperSymbol] || null;
  }
};

export default {
  searchStockByName,
  get5paisaSnapshot,
  searchScripmaster,
  searchScripCode,
  getScripCode,
  SCRIP_CODES,
};
