import { API_ENDPOINTS } from '../config/api';

// Get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('token');
};

// Change user password
export const changePassword = async (currentPassword, newPassword) => {
  try {
    const token = getAuthToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    const response = await fetch(API_ENDPOINTS.CHANGE_PASSWORD, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to change password');
    }

    return { success: true, message: data.message };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

// Delete user account
export const deleteAccount = async (password) => {
  try {
    const token = getAuthToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    const response = await fetch(API_ENDPOINTS.DELETE_ACCOUNT, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to delete account');
    }

    return { success: true, message: data.message };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

// Get theme from localStorage
export const getTheme = () => {
  return localStorage.getItem('theme') || 'dark';
};

// Set theme to localStorage and apply to document
export const setTheme = (theme) => {
  localStorage.setItem('theme', theme);
  document.documentElement.setAttribute('data-theme', theme);
};

// Initialize theme on app load
export const initializeTheme = () => {
  const theme = getTheme();
  document.documentElement.setAttribute('data-theme', theme);
  return theme;
};
