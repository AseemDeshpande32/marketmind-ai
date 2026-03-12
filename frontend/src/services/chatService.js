import { API_ENDPOINTS } from '../config/api';

/**
 * Send a chat message to the MarketMind AI backend.
 *
 * @param {string} message - The user's message text.
 * @param {Array} history - Conversation history [{"role": "user"|"assistant", "content": "..."}]
 * @returns {Promise<{ response: string, intent: string, data: object|null }>}
 */
export const sendChatMessage = async (message, history = []) => {
  const response = await fetch(API_ENDPOINTS.CHAT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });

  const data = await response.json();

  if (!response.ok) {
    // Return a structured error so the UI can display the Ollama message gracefully
    throw new Error(data.message || data.error || 'Chat request failed');
  }

  return data;
};

/**
 * Stream a chat message from the MarketMind AI backend via SSE.
 *
 * Calls onMeta once with { intent, data } before tokens arrive.
 * Calls onToken for every text chunk produced by the model.
 * Calls onDone when the stream finishes.
 * Calls onError with an Error object if something goes wrong.
 *
 * @param {string}      message
 * @param {Array}       history  conversation history [{"role": "user"|"assistant", "content": "..."}]
 * @param {Function}    onToken  (text: string) => void
 * @param {Function}    onMeta   ({ intent, data }) => void
 * @param {Function}    onDone   () => void
 * @param {Function}    onError  (err: Error) => void
 * @param {AbortSignal} [signal] optional AbortSignal to cancel the stream
 */
export const streamChatMessage = async (message, history, onToken, onMeta, onDone, onError, signal) => {
  let response;
  try {
    response = await fetch(API_ENDPOINTS.CHAT_STREAM, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
      signal,
    });
  } catch (err) {
    onError(new Error('Network error — could not reach the server.'));
    return;
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    onError(new Error(data.message || data.error || 'Chat request failed'));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep any incomplete line for next chunk

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'meta')  onMeta(event);
          else if (event.type === 'token') onToken(event.text);
          else if (event.type === 'done')  onDone();
          else if (event.type === 'error') onError(new Error(event.message));
        } catch (_) { /* ignore malformed SSE lines */ }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      onDone(); // user stopped — treat as clean completion
    } else {
      onError(new Error('Stream interrupted: ' + err.message));
    }
  }
};

export default { sendChatMessage, streamChatMessage };
