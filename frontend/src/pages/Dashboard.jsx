import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiSearch, FiTrendingUp, FiTrendingDown, FiClock } from 'react-icons/fi'
import './Dashboard.css'

const Dashboard = () => {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')

  const trendingStocks = [
    { symbol: 'AAPL', name: 'Apple Inc.', price: 178.52, change: 2.45, isUp: true },
    { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 141.80, change: 1.23, isUp: true },
    { symbol: 'MSFT', name: 'Microsoft Corp.', price: 378.91, change: -0.87, isUp: false },
    { symbol: 'TSLA', name: 'Tesla Inc.', price: 248.50, change: 3.21, isUp: true },
    { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 178.25, change: -1.15, isUp: false },
    { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 495.22, change: 4.56, isUp: true },
  ]

  const newsItems = [
    {
      id: 1,
      title: 'Fed Signals Potential Rate Cuts in 2026',
      source: 'Reuters',
      time: '2 hours ago',
      category: 'Economy'
    },
    {
      id: 2,
      title: 'Tech Stocks Rally on Strong Earnings Reports',
      source: 'Bloomberg',
      time: '4 hours ago',
      category: 'Technology'
    },
    {
      id: 3,
      title: 'AI Investments Continue to Drive Market Growth',
      source: 'CNBC',
      time: '5 hours ago',
      category: 'AI'
    },
    {
      id: 4,
      title: 'Energy Sector Shows Signs of Recovery',
      source: 'Wall Street Journal',
      time: '6 hours ago',
      category: 'Energy'
    },
    {
      id: 5,
      title: 'Cryptocurrency Markets See Increased Institutional Interest',
      source: 'Financial Times',
      time: '8 hours ago',
      category: 'Crypto'
    }
  ]

  const handleSearch = (e) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/stock/${searchQuery.toUpperCase()}`)
    }
  }

  const handleStockClick = (symbol) => {
    navigate(`/stock/${symbol}`)
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="welcome-section">
          <h1>Welcome back!</h1>
          <p>Here's what's happening in the market today</p>
        </div>
        
        <form className="search-bar" onSubmit={handleSearch}>
          <FiSearch className="search-icon" />
          <input
            type="text"
            placeholder="Search stocks by symbol (e.g., AAPL, GOOGL)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button type="submit">Search</button>
        </form>
      </div>

      <div className="dashboard-content">
        {/* Trending Stocks Section */}
        <section className="trending-section">
          <h2>
            <FiTrendingUp /> Trending Stocks
          </h2>
          <div className="stocks-grid">
            {trendingStocks.map((stock) => (
              <div
                key={stock.symbol}
                className="stock-card"
                onClick={() => handleStockClick(stock.symbol)}
              >
                <div className="stock-info">
                  <span className="stock-symbol">{stock.symbol}</span>
                  <span className="stock-name">{stock.name}</span>
                </div>
                <div className="stock-data">
                  <span className="stock-price">${stock.price.toFixed(2)}</span>
                  <span className={`stock-change ${stock.isUp ? 'positive' : 'negative'}`}>
                    {stock.isUp ? <FiTrendingUp /> : <FiTrendingDown />}
                    {stock.isUp ? '+' : ''}{stock.change.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Market News Section */}
        <section className="news-section">
          <h2>
            <FiClock /> Latest Market News
          </h2>
          <div className="news-list">
            {newsItems.map((news) => (
              <article key={news.id} className="news-card">
                <div className="news-content">
                  <span className="news-category">{news.category}</span>
                  <h3>{news.title}</h3>
                  <div className="news-meta">
                    <span className="news-source">{news.source}</span>
                    <span className="news-time">{news.time}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

export default Dashboard
