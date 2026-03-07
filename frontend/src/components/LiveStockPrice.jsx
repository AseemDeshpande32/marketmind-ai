/**
 * Live Stock Price Widget - Shows real-time price with WebSocket
 */
import { useState, useEffect } from 'react';
import { FiActivity, FiTrendingUp, FiTrendingDown } from 'react-icons/fi';
import { get5paisaSnapshot } from '../services/market5paisaService';
import useStockWebSocket from '../hooks/useStockWebSocket';
import './LiveStockPrice.css';

const LiveStockPrice = ({ scripCode, showDetails = true }) => {
  const [snapshot, setSnapshot] = useState(null);
  const [currentPrice, setCurrentPrice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // WebSocket for live updates
  const { liveData, isConnected } = useStockWebSocket(scripCode);

  // Fetch initial snapshot
  useEffect(() => {
    const fetchSnapshot = async () => {
      try {
        setLoading(true);
        const data = await get5paisaSnapshot(scripCode);
        setSnapshot(data);
        setCurrentPrice(data.price);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Error fetching snapshot:', err);
      } finally {
        setLoading(false);
      }
    };

    if (scripCode) {
      fetchSnapshot();
    }
  }, [scripCode]);

  // Update price from WebSocket
  useEffect(() => {
    if (liveData) {
      const newPrice = liveData.LastTradedPrice || liveData.LastRate || liveData.LTP;
      if (newPrice) {
        setCurrentPrice(parseFloat(newPrice));
      }
    }
  }, [liveData]);

  if (loading) {
    return (
      <div className="live-stock-price loading">
        <div className="spinner"></div>
        <p>Loading stock data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="live-stock-price error">
        <p>❌ {error}</p>
      </div>
    );
  }

  if (!snapshot) {
    return null;
  }

  const isPositive = snapshot.change >= 0;
  const priceToShow = currentPrice || snapshot.price;

  return (
    <div className="live-stock-price">
      <div className="price-header">
        <div className="live-indicator">
          <FiActivity className={isConnected ? 'live-active' : 'live-inactive'} />
          <span>{isConnected ? 'LIVE' : 'DELAYED'}</span>
        </div>
        <h2 className="stock-name">{snapshot.name || `Scrip ${scripCode}`}</h2>
      </div>

      <div className="price-display">
        <h1 className="current-price">₹{priceToShow?.toFixed(2)}</h1>
        <div className={`price-change ${isPositive ? 'positive' : 'negative'}`}>
          {isPositive ? <FiTrendingUp /> : <FiTrendingDown />}
          <span>
            {isPositive ? '+' : ''}{snapshot.change?.toFixed(2)} ({snapshot.changePercent?.toFixed(2)}%)
          </span>
        </div>
      </div>

      {showDetails && (
        <div className="price-details">
          <div className="detail-row">
            <span>Open:</span>
            <span>₹{snapshot.open?.toFixed(2)}</span>
          </div>
          <div className="detail-row">
            <span>High:</span>
            <span className="high">₹{snapshot.high?.toFixed(2)}</span>
          </div>
          <div className="detail-row">
            <span>Low:</span>
            <span className="low">₹{snapshot.low?.toFixed(2)}</span>
          </div>
          <div className="detail-row">
            <span>Prev Close:</span>
            <span>₹{snapshot.prevClose?.toFixed(2)}</span>
          </div>
          {snapshot.volume && (
            <div className="detail-row">
              <span>Volume:</span>
              <span>{snapshot.volume?.toLocaleString()}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LiveStockPrice;
