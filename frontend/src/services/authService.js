import { API_ENDPOINTS } from '../config/api';

// Get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('token');
};

// Set auth token to localStorage
export const setAuthToken = (token) => {
  localStorage.setItem('token', token);
};

// Remove auth token from localStorage
export const removeAuthToken = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return !!getAuthToken();
};

// Register new user
export const register = async (name, email, password) => {
  try {
    const response = await fetch(API_ENDPOINTS.REGISTER, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Registration failed');
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

// Login user
export const login = async (email, password) => {
  try {
    const response = await fetch(API_ENDPOINTS.LOGIN, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Login failed');
    }

    // Save token and user info
    if (data.access_token) {
      setAuthToken(data.access_token);
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

// Get current user info
export const getCurrentUser = async () => {
  try {
    const token = getAuthToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    const response = await fetch(API_ENDPOINTS.ME, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to get user info');
    }

    // Save user info to localStorage
    localStorage.setItem('user', JSON.stringify(data));

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

// Logout user
export const logout = () => {
  removeAuthToken();
  window.location.href = '/login';
};
