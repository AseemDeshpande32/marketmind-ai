import { useEffect, useRef, useState, useCallback } from 'react';
import { io } from 'socket.io-client';

// Derive Socket.IO server URL from the API base URL (strip "/api" suffix)
const SOCKET_URL =
  (import.meta.env.VITE_API_URL || 'http://localhost:5000/api')
    .replace(/\/api\/?$/, '');

/**
 * useStockWebSocket
 *
 * Connects to the Flask-SocketIO server and subscribes to live price
 * updates for the given scrip code.
 *
 * @param {object} params
 * @param {number|null} params.scripCode     - 5paisa scrip code (e.g. 2885)
 * @param {string}      params.exchange      - "N" (NSE) or "B" (BSE)
 * @param {string}      params.exchangeType  - "C" (cash, default)
 *
 * @returns {{ liveData: object|null, isConnected: boolean, error: string|null }}
 */
export function useStockWebSocket({
  scripCode,
  exchange = 'N',
  exchangeType = 'C',
}) {
  const socketRef    = useRef(null);
  const [liveData,    setLiveData]    = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error,       setError]       = useState(null);

  const subscribe = useCallback((socket) => {
    if (!scripCode) return;
    console.log(`🔌 Subscribing to scrip ${scripCode} on ${SOCKET_URL}`);
    socket.emit('subscribe_stock', {
      scrip_code:    scripCode,
      exchange,
      exchange_type: exchangeType,
    });
  }, [scripCode, exchange, exchangeType]);

  useEffect(() => {
    if (!scripCode) return;

    // Create (or reuse) the socket connection
    const socket = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 2000,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('✅ Socket.IO connected');
      setIsConnected(true);
      setError(null);
      subscribe(socket);
    });

    socket.on('disconnect', () => {
      console.log('🔌 Socket.IO disconnected');
      setIsConnected(false);
    });

    socket.on('connect_error', (err) => {
      console.error('❌ Socket.IO connect error:', err.message);
      setError(err.message);
      setIsConnected(false);
    });

    // Live price updates from the backend
    socket.on('stock_update', (data) => {
      // Only accept events for the subscribed scrip
      if (data.scrip_code && Number(data.scrip_code) !== Number(scripCode)) return;
      setLiveData(data);
    });

    return () => {
      console.log(`🔌 Unsubscribing from scrip ${scripCode}`);
      socket.emit('unsubscribe_stock', { scrip_code: scripCode });
      socket.disconnect();
      socketRef.current = null;
      setIsConnected(false);
      setLiveData(null);
    };
  }, [scripCode, exchange, exchangeType, subscribe]);

  return { liveData, isConnected, error };
}
