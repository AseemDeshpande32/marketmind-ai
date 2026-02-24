// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export const API_ENDPOINTS = {
  // Auth endpoints
  REGISTER: `${API_BASE_URL}/auth/register`,
  LOGIN: `${API_BASE_URL}/auth/login`,
  ME: `${API_BASE_URL}/auth/me`,
  CHANGE_PASSWORD: `${API_BASE_URL}/auth/change-password`,
  DELETE_ACCOUNT: `${API_BASE_URL}/auth/delete-account`,
  
  // News endpoints
  NEWS: `${API_BASE_URL}/news`,
  NEWS_HEALTH: `${API_BASE_URL}/news/health`,
  
  // Stock endpoints
  STOCKS: `${API_BASE_URL}/stocks`,
  STOCK_SEARCH: `${API_BASE_URL}/stocks/search`,
};

export default API_BASE_URL;
