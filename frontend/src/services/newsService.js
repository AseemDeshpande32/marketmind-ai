import { API_ENDPOINTS } from '../config/api';

// Get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('token');
};

// Fetch latest news
export const fetchNews = async (category = null, limit = 20) => {
  try {
    let url = API_ENDPOINTS.NEWS;
    const params = new URLSearchParams();
    
    if (category) params.append('category', category);
    if (limit) params.append('limit', limit);
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to fetch news');
    }

    return { success: true, data: data.data, count: data.count };
  } catch (error) {
    return { success: false, error: error.message, data: [] };
  }
};

// Check news service health
export const checkNewsHealth = async () => {
  try {
    const response = await fetch(API_ENDPOINTS.NEWS_HEALTH, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    return { success: response.ok, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};
