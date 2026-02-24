import { API_ENDPOINTS } from '../config/api';

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
 * Get trending stocks (placeholder for future implementation)
 * @returns {Promise<Array>} Array of trending stocks
 */
export const getTrendingStocks = async () => {
  // This can be implemented later when backend has trending endpoint
  return [];
};

export default {
  searchStock,
  getTrendingStocks,
};
