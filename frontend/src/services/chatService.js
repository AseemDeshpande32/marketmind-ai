import { API_ENDPOINTS } from '../config/api';

/**
 * Send a chat message to the MarketMind AI backend.
 *
 * @param {string} message - The user's message text.
 * @returns {Promise<{ response: string, intent: string, data: object|null }>}
 */
export const sendChatMessage = async (message) => {
  const response = await fetch(API_ENDPOINTS.CHAT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  const data = await response.json();

  if (!response.ok) {
    // Return a structured error so the UI can display the Ollama message gracefully
    throw new Error(data.message || data.error || 'Chat request failed');
  }

  return data;
};

export default { sendChatMessage };
