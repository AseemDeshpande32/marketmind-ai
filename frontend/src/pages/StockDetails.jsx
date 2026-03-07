import { useParams, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import { FiArrowLeft, FiTrendingUp, FiTrendingDown, FiBarChart2, FiActivity } from 'react-icons/fi'
import { searchStock } from '../services/stockService'
import { searchStockByName } from '../services/market5paisaService'
import { useStockWebSocket } from '../hooks/useStockWebSocket'
import CandlestickChart from '../components/CandlestickChart'
import './StockDetails.css'

// Check if NSE/BSE market is currently open
const isMarketOpen = () => {
  const now = new Date()
  const day = now.getDay() // 0=Sunday, 6=Saturday
  const hour = now.getHours()
  const minute = now.getMinutes()
  
  // Market closed on weekends
  if (day === 0 || day === 6) return false
  
  // Market hours: 9:15 AM - 3:30 PM IST (Mon-Fri)
  const currentTime = hour * 60 + minute
  const marketOpen = 9 * 60 + 15  // 9:15 AM
  const marketClose = 15 * 60 + 30 // 3:30 PM
  
  return currentTime >= marketOpen && currentTime < marketClose
}

const StockDetails = () => {
  const { symbol } = useParams()
  const navigate = useNavigate()

  // ── State ──────────────────────────────────────────────────────────────────
  const [stockData,  setStockData]  = useState(null)
  const [scripCode,  setScripCode]  = useState(null)
  const [exchange,   setExchange]   = useState('N')      // "N" = NSE, "B" = BSE
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)

  // Live price state
  const [livePrice,         setLivePrice]         = useState(null)
  const [liveChange,        setLiveChange]        = useState(null)
  const [liveChangePercent, setLiveChangePercent] = useState(null)
  const [liveHigh,          setLiveHigh]          = useState(null)
  const [liveLow,           setLiveLow]           = useState(null)
  const [liveVolume,        setLiveVolume]         = useState(null)
  const [prevClose,         setPrevClose]          = useState(null)
  const [priceFlash, setPriceFlash] = useState(null)  // 'up' | 'down' | null
  const [marketOpen, setMarketOpen] = useState(isMarketOpen())

  // Check market hours periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setMarketOpen(isMarketOpen())
    }, 60000) // Check every minute
    return () => clearInterval(interval)
  }, [])

  // WebSocket hook
  const { liveData, isConnected } = useStockWebSocket({
    scripCode,
    exchange,
    exchangeType: 'C',
  })

  // ── Fetch snapshot data ────────────────────────────────────────────────────
  const fetchStockData = useCallback(async () => {
    if (!symbol) return
    try {
      setLoading(true)
      setError(null)

      // Try 5paisa route first → falls back to generic search
      let data
      try {
        data = await searchStockByName(symbol, exchange)
      } catch {
        data = await searchStock(symbol)
      }

      setStockData(data)
      setScripCode(data.scripCode || null)
      setPrevClose(data.prevClose ?? null)

      // Seed live values from snapshot
      setLivePrice(data.price ?? null)
      setLiveChange(data.change ?? null)
      setLiveChangePercent(data.changePercent ?? null)
      setLiveHigh(data.high ?? null)
      setLiveLow(data.low ?? null)
      setLiveVolume(data.volume ?? null)
    } catch (err) {
      setError(err.message || 'Failed to fetch stock data')
      console.error('Error fetching stock:', err)
    } finally {
      setLoading(false)
    }
  }, [symbol, exchange])

  useEffect(() => { fetchStockData() }, [fetchStockData])

  // ── Process WebSocket ticks ────────────────────────────────────────────────
  useEffect(() => {
    if (!liveData) return
    const price = parseFloat(liveData.LastTradedPrice ?? liveData.LastRate ?? 0)
    if (!price) return

    setLivePrice(price)
    if (liveData.High)   setLiveHigh(parseFloat(liveData.High))
    if (liveData.Low)    setLiveLow(parseFloat(liveData.Low))
    if (liveData.Volume || liveData.TotalQty)
      setLiveVolume(parseInt(liveData.Volume || liveData.TotalQty, 10))

    // Use pre-computed change from payload, else derive from prevClose
    if (liveData.Change !== undefined) {
      setLiveChange(parseFloat(liveData.Change))
      setLiveChangePercent(parseFloat(liveData.ChangePercent ?? 0))
    } else {
      const pc = prevClose ?? stockData?.prevClose
      if (pc) {
        const ch = price - pc
        setLiveChange(ch)
        setLiveChangePercent((ch / pc) * 100)
      }
    }

    // Direction-aware flash
    const prevPrice = livePrice ?? stockData?.price
    if (prevPrice && price !== prevPrice) {
      setPriceFlash(price > prevPrice ? 'up' : 'down')
      const t = setTimeout(() => setPriceFlash(null), 700)
      return () => clearTimeout(t)
    }
  }, [liveData, prevClose, stockData])


  // ── Derived display values ────────────────────────────────────────────────
  const displayPrice   = livePrice   ?? stockData?.price
  const displayChange  = liveChange  ?? stockData?.change
  const displayPct     = liveChangePercent ?? stockData?.changePercent
  const displayHigh    = liveHigh    ?? stockData?.high
  const displayLow     = liveLow     ?? stockData?.low
  const displayVolume  = liveVolume  ?? stockData?.volume
  const isPositive     = (displayChange ?? 0) >= 0
  const exchLabel      = exchange === 'N' ? 'NSE' : 'BSE'

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="stock-details">
      <button className="back-button" onClick={() => navigate('/dashboard')}>
        <FiArrowLeft /> Back to Dashboard
      </button>

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading stock data...</p>
        </div>
      )}

      {error && (
        <div className="error-container">
          <h2>Stock Not Found</h2>
          <p>{error}</p>
          <p style={{ color: '#a0a0b0', fontSize: '0.9rem', marginTop: '0.5rem' }}>
            Try searching for a valid NSE/BSE symbol (e.g.&nbsp;<strong>RELIANCE</strong>, <strong>TCS</strong>, <strong>INFY</strong>).
          </p>
          <button onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
        </div>
      )}

      {!loading && !error && stockData && (
        <>
          {/* Header ───────────────────────────────────────────────────────── */}
          <div className="stock-header">
            <div className="stock-title">
              <h1>{stockData.symbol}</h1>
              <span className="company-name">{stockData.name}</span>

              {/* NSE / BSE Toggle */}
              <div className="exchange-toggle">
                <button
                  className={`toggle-btn ${exchange === 'N' ? 'active' : ''}`}
                  onClick={() => setExchange('N')}
                >NSE</button>
                <button
                  className={`toggle-btn ${exchange === 'B' ? 'active' : ''}`}
                  onClick={() => setExchange('B')}
                >BSE</button>
              </div>
            </div>

            <div className="stock-price-section">
              {/* Live / Connecting badge */}
              <span className={`live-badge ${isConnected && marketOpen ? 'connected' : ''}`}>
                {isConnected && marketOpen ? '● LIVE' : marketOpen ? '○ CONNECTING' : '○ CLOSED'}
              </span>

              <span className={`current-price ${priceFlash ? `flash-${priceFlash}` : ''}`}>
                ₹{displayPrice?.toFixed(2)}
              </span>

              <span className={`price-change ${isPositive ? 'positive' : 'negative'}`}>
                {isPositive ? <FiTrendingUp /> : <FiTrendingDown />}
                {isPositive ? '+' : ''}₹{displayChange?.toFixed(2)} ({displayPct?.toFixed(2)}%)
              </span>
            </div>
          </div>

          <div className="stock-content">
            {/* Candlestick Chart ─────────────────────────────────────────── */}
            <div className="chart-section">
              <h2><FiActivity /> Price Chart</h2>
              {scripCode ? (
                <CandlestickChart
                  scripCode={scripCode}
                  exchange={exchange}
                  symbol={stockData.symbol}
                />
              ) : (
                <p style={{ color: '#a0a0b0' }}>
                  Scrip code not available — chart cannot load.
                </p>
              )}
            </div>

            {/* Key Statistics ────────────────────────────────────────────── */}
            <div className="stats-section">
              <h2><FiBarChart2 /> Key Statistics</h2>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-label">Open</span>
                  <span className="stat-value">₹{stockData.open?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">High</span>
                  <span className="stat-value">₹{displayHigh?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Low</span>
                  <span className="stat-value">₹{displayLow?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Prev Close</span>
                  <span className="stat-value">₹{stockData.prevClose?.toFixed(2) || 'N/A'}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Volume</span>
                  <span className="stat-value">
                    {displayVolume != null ? displayVolume.toLocaleString() : 'N/A'}
                  </span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Exchange</span>
                  <span className="stat-value">{exchLabel}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default StockDetails
