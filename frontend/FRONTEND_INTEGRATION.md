# Frontend Integration Guide - 5paisa Live Market Data

## 📦 Installation

```bash
cd frontend
npm install socket.io-client
```

## 🔌 Backend API Endpoints

### 1. REST API - Market Snapshot

```javascript
// Get stock snapshot (5paisa)
const response = await fetch('http://localhost:5000/api/stocks/5paisa/snapshot/1660?exchange=N');
const data = await response.json();

// Response format:
{
  "symbol": "1660",
  "name": "ScripCode 1660",
  "price": 313.75,
  "change": -3.70,
  "changePercent": -1.17,
  "open": 316.00,
  "high": 318.40,
  "low": 313.25,
  "volume": 8730618,
  "prevClose": 317.45,
  "week52High": 444.20,
  "week52Low": 302.00,
  "currency": "INR",
  "exchange": "N",
  "exchangeType": "C",
  "upperCircuit": 349.15,
  "lowerCircuit": 285.75
}
```

### 2. WebSocket - Live Updates

```javascript
import io from 'socket.io-client';

// Connect to WebSocket
const socket = io('http://localhost:5000');

// Handle connection
socket.on('connect', () => {
  console.log('Connected to backend');
});

// Subscribe to live data
socket.emit('subscribe_stock', {
  scrip_code: 1660,
  exchange: 'N',
  exchange_type: 'C'
});

// Listen for live updates
socket.on('stock_update', (data) => {
  console.log('Live update:', data);
  // Update your UI with real-time data
});

// Unsubscribe when done
socket.emit('unsubscribe_stock', {
  scrip_code: 1660
});
```

---

## 🎨 React Component Example

```jsx
// StockDetails.jsx
import { useState, useEffect } from 'react';
import io from 'socket.io-client';

export default function StockDetails({ scripCode }) {
  const [stockData, setStockData] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Fetch initial snapshot
    const fetchSnapshot = async () => {
      try {
        const response = await fetch(
          `http://localhost:5000/api/stocks/5paisa/snapshot/${scripCode}?exchange=N`
        );
        const data = await response.json();
        setStockData(data);
        setLivePrice(data.price);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching stock:', error);
        setLoading(false);
      }
    };

    fetchSnapshot();

    // 2. Connect to WebSocket for live updates
    const socket = io('http://localhost:5000');

    socket.on('connect', () => {
      console.log('WebSocket connected');
      
      // Subscribe to stock updates
      socket.emit('subscribe_stock', {
        scrip_code: scripCode,
        exchange: 'N',
        exchange_type: 'C'
      });
    });

    socket.on('subscribed', (data) => {
      console.log('Subscribed:', data);
    });

    socket.on('stock_update', (data) => {
      // Update live price
      const lastPrice = data.LastTradedPrice || data.LastRate || data.LTP;
      if (lastPrice) {
        setLivePrice(lastPrice);
      }
    });

    socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    // Cleanup on unmount
    return () => {
      socket.emit('unsubscribe_stock', { scrip_code: scripCode });
      socket.disconnect();
    };
  }, [scripCode]);

  if (loading) return <div>Loading...</div>;
  if (!stockData) return <div>Stock not found</div>;

  return (
    <div className="stock-details">
      <h2>{stockData.name}</h2>
      <div className="price-section">
        <h1 className="live-price">₹{livePrice || stockData.price}</h1>
        <span className={stockData.change >= 0 ? 'positive' : 'negative'}>
          {stockData.change >= 0 ? '+' : ''}{stockData.change} 
          ({stockData.changePercent}%)
        </span>
      </div>

      <div className="stock-stats">
        <div>Open: ₹{stockData.open}</div>
        <div>High: ₹{stockData.high}</div>
        <div>Low: ₹{stockData.low}</div>
        <div>Prev Close: ₹{stockData.prevClose}</div>
        <div>Volume: {stockData.volume.toLocaleString()}</div>
        <div>52W High: ₹{stockData.week52High}</div>
        <div>52W Low: ₹{stockData.week52Low}</div>
      </div>
    </div>
  );
}
```

---

## 🔄 Replacing Old API with 5paisa

### Before (Old API):
```javascript
// Old code
fetch('/api/stocks/search?symbol=RELIANCE')
```

### After (5paisa Snapshot):
```javascript
// New code - Use scrip code instead of symbol
fetch('/api/stocks/5paisa/snapshot/1660?exchange=N')
```

---

## 📊 Common Scrip Codes

```javascript
const SCRIP_CODES = {
  RELIANCE: 1660,
  TCS: 11536,
  INFY: 1594,
  HDFC: 1330,
  ICICI: 4963,
  // Add more as needed
};

// Usage
fetch(`/api/stocks/5paisa/snapshot/${SCRIP_CODES.RELIANCE}`);
```

---

## 🛠️ Installation & Setup

### Backend Setup:

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Make sure .env has:
# APP_KEY=your_app_key
# ENCRYPTION_KEY=your_encryption_key
# USER_ID=your_user_id
# APP_SOURCE=your_app_source
# REQUEST_TOKEN=your_request_token

# Generate access token
python 5paisa_auth.py

# Run backend
python run.py
```

### Frontend Setup:

```bash
cd frontend

# Install socket.io-client
npm install socket.io-client

# Update API base URL if needed
# (usually in .env or config file)
VITE_API_URL=http://localhost:5000
```

---

## ⚡ Quick Integration Checklist

- [ ] Install `socket.io-client` in frontend
- [ ] Update backend dependencies: `pip install -r requirements.txt`
- [ ] Generate 5paisa access token: `python 5paisa_auth.py`
- [ ] Replace old stock API calls with new endpoints
- [ ] Add WebSocket connection for live data
- [ ] Update scrip code mapping (symbol → scrip_code)
- [ ] Test snapshot endpoint
- [ ] Test WebSocket subscriptions
- [ ] Add error handling for expired tokens

---

## 🚨 Important Notes

1. **Token Expiry**: Access tokens expire after ~24 hours. Run `python 5paisa_auth.py` to refresh.
2. **Scrip Codes**: Use numeric scrip codes, not text symbols (e.g., 1660 not "RELIANCE")
3. **WebSocket Rooms**: Each stock creates a separate room for efficient broadcasting
4. **CORS**: Already configured for `http://localhost:3000` and `http://localhost:5173`

---

## 🐛 Troubleshooting

### "Invalid Token" Error
```bash
# Solution: Regenerate access token
python 5paisa_auth.py
```

### WebSocket Not Connecting
```bash
# Check if socketio is running
# Run backend with: python run.py (not flask run)
```

### No Live Updates
```bash
# Check token_store.json exists
# Check 5paisa WebSocket is connected in backend logs
```

---

## 📝 Next Steps

1. **Replace old API calls** with `/api/stocks/5paisa/snapshot/<scrip_code>`
2. **Add WebSocket integration** for live price updates
3. **Create scrip code mapping** for symbol → scrip_code conversion
4. **Test with multiple stocks** to ensure scalability
5. **Add token refresh mechanism** for production

---

**Ready to integrate? Start with the REST API, then add WebSocket for live updates!** 🚀
