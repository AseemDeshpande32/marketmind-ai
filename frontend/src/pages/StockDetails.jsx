import { useParams, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { FiArrowLeft, FiTrendingUp, FiTrendingDown, FiBarChart2, FiActivity } from 'react-icons/fi'
import { searchStock } from '../services/stockService'
import './StockDetails.css'

const StockDetails = () => {
  const { symbol } = useParams()
  const navigate = useNavigate()
  const [stockData, setStockData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchStockData = async () => {
      if (!symbol) return;
      
      try {
        setLoading(true)
        setError(null)
        const data = await searchStock(symbol)
        setStockData(data)
      } catch (err) {
        setError(err.message || 'Failed to fetch stock data')
        console.error('Error fetching stock:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchStockData()
  }, [symbol])

  // Load TradingView widget
  useEffect(() => {
    if (stockData && stockData.symbol) {
      // Clear any existing chart
      const chartContainer = document.getElementById('tradingview_chart')
      if (chartContainer) {
        chartContainer.innerHTML = ''
      }

      // Map Indian stock symbols to TradingView format
      // BSE exchange is better supported in free TradingView widget
      const cleanSymbol = stockData.symbol.replace('.NS', '').replace('.BO', '')
      const tvSymbol = `BSE:${cleanSymbol}`
      
      // Check if TradingView library is already loaded
      if (window.TradingView) {
        new window.TradingView.widget({
          autosize: true,
          symbol: tvSymbol,
          interval: 'D',
          timezone: 'Asia/Kolkata',
          theme: 'dark',
          style: '1',
          locale: 'en',
          toolbar_bg: '#1a1a2e',
          enable_publishing: false,
          hide_side_toolbar: false,
          allow_symbol_change: true,
          container_id: 'tradingview_chart',
          height: 400,
          width: '100%'
        })
      } else {
        // Load TradingView script if not already loaded
        const script = document.createElement('script')
        script.src = 'https://s3.tradingview.com/tv.js'
        script.async = true
        script.onload = () => {
          if (window.TradingView) {
            new window.TradingView.widget({
              autosize: true,
              symbol: tvSymbol,
              interval: 'D',
              timezone: 'Asia/Kolkata',
              theme: 'dark',
              style: '1',
              locale: 'en',
              toolbar_bg: '#1a1a2e',
              enable_publishing: false,
              hide_side_toolbar: false,
              allow_symbol_change: true,
              container_id: 'tradingview_chart',
              height: 400,
              width: '100%'
            })
          }
        }
        document.head.appendChild(script)
      }
    }
  }, [stockData])

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
          <h2>Error Loading Stock</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
        </div>
      )}

      {!loading && !error && stockData && (
        <>
      <div className="stock-header">
        <div className="stock-title">
          <h1>{stockData.symbol}</h1>
          <span className="company-name">{stockData.name}</span>
        </div>
        <div className="stock-price-section">
          <span className="current-price">₹{stockData.price?.toFixed(2)}</span>
          <span className={`price-change ${stockData.change >= 0 ? 'positive' : 'negative'}`}>
            {stockData.change >= 0 ? <FiTrendingUp /> : <FiTrendingDown />}
            {stockData.change >= 0 ? '+' : ''}₹{stockData.change?.toFixed(2)} ({stockData.changePercent?.toFixed(2)}%)
          </span>
        </div>
      </div>

      <div className="stock-content">
        {/* Real TradingView Chart */}
        <div className="chart-section">
          <h2><FiActivity /> Live Price Chart</h2>
          <div className="chart-container">
            <div className="tradingview-widget-container">
              <div id="tradingview_chart"></div>
            </div>
          </div>
        </div>

        {/* Key Statistics */}
        <div className="stats-section">
          <h2><FiBarChart2 /> Key Statistics</h2>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Open</span>
              <span className="stat-value">₹{stockData.open?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">High</span>
              <span className="stat-value">₹{stockData.high?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Low</span>
              <span className="stat-value">₹{stockData.low?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Market Cap</span>
              <span className="stat-value">{stockData.marketCap || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">P/E Ratio</span>
              <span className="stat-value">{stockData.peRatio?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">52W High</span>
              <span className="stat-value">₹{stockData.week52High?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">52W Low</span>
              <span className="stat-value">₹{stockData.week52Low?.toFixed(2) || 'N/A'}</span>
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
