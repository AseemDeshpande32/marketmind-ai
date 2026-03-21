import { API_ENDPOINTS } from '../config/api';

const getAuthToken = () => localStorage.getItem('token');

/**
 * Stock Service - handles all stock-related API calls
 */

/**
 * Search for a stock by symbol
 * @param {string} symbol - Stock ticker symbol (e.g., 'TCS', 'RELIANCE')
 * @returns {Promise<Object>} Stock data
 */
export const searchStock = async (symbol) => {
  try {
    const response = await fetch(`${API_ENDPOINTS.STOCKS}/search?symbol=${symbol}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || data.error || 'Failed to fetch stock data');
    }

    return data;
  } catch (error) {
    console.error('Error fetching stock:', error);
    throw error;
  }
};

/**
 * Get trending stocks sorted by volume from the backend
 * @param {number} limit - Number of stocks to return (max 10)
 * @returns {Promise<Array>} Array of trending stocks
 */
export const getTrendingStocks = async (limit = 4) => {
  try {
    const response = await fetch(`${API_ENDPOINTS.STOCKS}/trending?limit=${limit}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Failed to fetch trending stocks');
    return data.trending || [];
  } catch (error) {
    console.error('Error fetching trending stocks:', error);
    return [];
  }
};

export const getWatchlist = async () => {
  const token = getAuthToken();
  if (!token) return [];

  const response = await fetch(API_ENDPOINTS.STOCK_WATCHLIST, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to load watchlist');
  }
  return data.watchlist || [];
};

export const addToWatchlist = async ({ symbol, name, exchange = 'NSE' }) => {
  const token = getAuthToken();
  if (!token) throw new Error('Please log in to manage watchlist');

  const response = await fetch(API_ENDPOINTS.STOCK_WATCHLIST, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ symbol, name, exchange }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to add symbol to watchlist');
  }
  return data.item;
};

export const removeFromWatchlist = async (symbol) => {
  const token = getAuthToken();
  if (!token) throw new Error('Please log in to manage watchlist');

  const response = await fetch(`${API_ENDPOINTS.STOCK_WATCHLIST}/${encodeURIComponent(symbol)}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to remove symbol from watchlist');
  }
  return data;
};

export const getBatchQuotes = async (symbols = []) => {
  if (!symbols.length) return [];

  const response = await fetch(`${API_ENDPOINTS.STOCK_SEARCH}/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ symbols }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Failed to fetch watchlist quotes');
  }

  return data.results || [];
};

export default {
  searchStock,
  getTrendingStocks,
  getWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  getBatchQuotes,
};
