/**
 * Custom hook for WebSocket connection to 5paisa live market data
 */
import { useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:5000';

/**
 * Hook for subscribing to live stock updates via WebSocket
 * @param {number} scripCode - Stock scrip code to subscribe to
 * @param {string} exchange - Exchange code (N=NSE, B=BSE)
 * @param {string} exchangeType - Exchange type (C=Cash, D=Derivative)
 * @returns {Object} { liveData, isConnected, error }
 */
export const useStockWebSocket = (scripCode, exchange = 'N', exchangeType = 'C') => {
  const [liveData, setLiveData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const socketRef = useRef(null);

  useEffect(() => {
    // Don't connect if no scrip code
    if (!scripCode) {
      console.log('⚠️ No scrip code provided, skipping WebSocket connection');
      return;
    }

    console.log(`🔌 Connecting to WebSocket for scrip: ${scripCode}, exchange: ${exchange}`);

    // Initialize socket connection
    socketRef.current = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    const socket = socketRef.current;

    // Connection handlers
    socket.on('connect', () => {
      console.log('✅ WebSocket connected, socket ID:', socket.id);
      setIsConnected(true);
      setError(null);

      // Subscribe to stock updates
      console.log(`📡 Subscribing to stock: ${scripCode}, exchange: ${exchange}`);
      socket.emit('subscribe_stock', {
        scrip_code: scripCode,
        exchange: exchange,
        exchange_type: exchangeType,
      });
    });

    socket.on('disconnect', () => {
      console.log('🔌 WebSocket disconnected');
      setIsConnected(false);
    });

    socket.on('connection_response', (data) => {
      console.log('Connection response:', data);
    });

    socket.on('subscribed', (data) => {
      console.log('✅ Subscribed to stock:', data);
    });

    socket.on('stock_update', (data) => {
      console.log('📊 Live update received:', {
        scripCode: data.ScripCode,
        price: data.LastTradedPrice || data.LastRate || data.LTP,
        high: data.High,
        low: data.Low,
        volume: data.Volume
      });
      setLiveData(data);
    });

    socket.on('error', (err) => {
      console.error('❌ WebSocket error:', err);
      setError(err.message || 'WebSocket error');
    });

    socket.on('connect_error', (err) => {
      console.error('Connection error:', err);
      setError('Failed to connect to live data stream');
      setIsConnected(false);
    });

    // Cleanup on unmount
    return () => {
      if (socket) {
        console.log(`🔌 Unsubscribing from stock: ${scripCode}`);
        socket.emit('unsubscribe_stock', {
          scrip_code: scripCode,
        });
        socket.disconnect();
        console.log('🔌 WebSocket disconnected');
      }
    };
  }, [scripCode, exchange, exchangeType]);

  return { liveData, isConnected, error };
};

/**
 * Hook for manually managing WebSocket connection
 * @returns {Object} { socket, isConnected, connect, disconnect, subscribe, unsubscribe }
 */
export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  const connect = () => {
    if (socketRef.current) return;

    socketRef.current = io(SOCKET_URL, {
      transports: ['websocket', 'polling'],
    });

    socketRef.current.on('connect', () => {
      setIsConnected(true);
    });

    socketRef.current.on('disconnect', () => {
      setIsConnected(false);
    });
  };

  const disconnect = () => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  };

  const subscribe = (scripCode, exchange = 'N', exchangeType = 'C') => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('subscribe_stock', {
        scrip_code: scripCode,
        exchange,
        exchange_type: exchangeType,
      });
    }
  };

  const unsubscribe = (scripCode) => {
    if (socketRef.current && isConnected) {
      socketRef.current.emit('unsubscribe_stock', {
        scrip_code: scripCode,
      });
    }
  };

  return {
    socket: socketRef.current,
    isConnected,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
  };
};

export default useStockWebSocket;
