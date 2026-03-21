import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiSearch, FiTrendingUp, FiTrendingDown, FiClock, FiStar } from 'react-icons/fi'
import { fetchNews } from '../services/newsService'
import { getWatchlist, getBatchQuotes } from '../services/stockService'
import { searchScripmaster } from '../services/market5paisaService'
import './Dashboard.css'

const Dashboard = () => {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [suggestions, setSuggestions]   = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const searchRef = useRef(null)
  const debounceRef = useRef(null)
  const [watchlistStocks, setWatchlistStocks] = useState([])
  const [watchlistLoading, setWatchlistLoading] = useState(true)
  const [watchlistError, setWatchlistError] = useState(null)
  const [newsItems, setNewsItems] = useState([])
  const [newsLoading, setNewsLoading] = useState(true)
  const [newsError, setNewsError] = useState(null)

  // Fetch watchlist stocks on mount
  useEffect(() => {
    const loadWatchlist = async () => {
      setWatchlistLoading(true)
      setWatchlistError(null)
      try {
        const list = await getWatchlist()
        if (!list.length) {
          setWatchlistStocks([])
          return
        }

        const symbols = list.map((item) => item.symbol)
        const quotes = await getBatchQuotes(symbols)
        const quoteBySymbol = new Map(quotes.map((q) => [q.symbol, q]))

        const merged = list.map((item) => {
          const quote = quoteBySymbol.get(item.symbol) || {}
          return {
            symbol: item.symbol,
            name: item.name || item.symbol,
            price: quote.current_price,
            change: quote.price_change,
            changePercent: quote.price_change_percent,
          }
        })

        setWatchlistStocks(merged)
      } catch (error) {
        console.error('Error loading watchlist:', error)
        setWatchlistError('Failed to load your watchlist')
      } finally {
        setWatchlistLoading(false)
      }
    }

    loadWatchlist()
  }, [])

  // Fetch news from backend on component mount
  useEffect(() => {
    loadNews()
  }, [])

  const loadNews = async () => {
    setNewsLoading(true)
    setNewsError(null)
    
    try {
      console.log('Fetching news from API...')
      const result = await fetchNews(null, 10)
      
      console.log('News API result:', result)
      
      if (result.success && result.data && result.data.length > 0) {
        // Transform backend news data to match frontend format
        const transformedNews = result.data.map((item, index) => ({
          id: index + 1,
          title: item.title,
          source: item.source || 'Unknown',
          time: formatTimeAgo(item.published_at),
          category: item.sentiment?.label || 'Market News',
          url: item.url,
          description: item.description,
          imageUrl: item.image_url,
          sentiment: item.sentiment
        }))
        setNewsItems(transformedNews)
        console.log('News loaded successfully:', transformedNews.length, 'items')
      } else {
        console.error('No news data available')
        setNewsError('No news available at the moment')
        setNewsItems([])
      }
    } catch (error) {
      console.error('News loading error:', error)
      setNewsError('Failed to load news. Please try again later.')
      setNewsItems([])
    } finally {
      setNewsLoading(false)
    }
  }

  // Helper function to format time ago
  const formatTimeAgo = (dateString) => {
    if (!dateString) return 'Recently'
    
    try {
      const date = new Date(dateString)
      const now = new Date()
      const diffMs = now - date
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
      
      if (diffHours < 1) return 'Less than 1 hour ago'
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
      if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
      return date.toLocaleDateString()
    } catch {
      return 'Recently'
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      setShowDropdown(false)
      navigate(`/stock/${searchQuery.trim().toUpperCase()}`)
    }
  }

  const handleSearchInput = (e) => {
    const val = e.target.value
    setSearchQuery(val)
    clearTimeout(debounceRef.current)
    if (val.trim().length < 2) { setSuggestions([]); setShowDropdown(false); return }
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchScripmaster(val.trim(), 'N')
        setSuggestions(res.results || [])
        setShowDropdown(true)
      } catch { setSuggestions([]) }
    }, 250)
  }

  const handleSuggestionClick = (sym) => {
    setShowDropdown(false)
    setSuggestions([])
    setSearchQuery(sym)
    navigate(`/stock/${sym}`)
  }

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => { if (searchRef.current && !searchRef.current.contains(e.target)) setShowDropdown(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

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
        
        <div className="search-wrapper" ref={searchRef}>
          <form className="search-bar" onSubmit={handleSearch}>
            <FiSearch className="search-icon" />
            <input
              type="text"
              placeholder="Search stocks by symbol (e.g., TCS, RELIANCE)..."
              value={searchQuery}
              onChange={handleSearchInput}
              onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
            />
            <button type="submit">Search</button>
          </form>
          {showDropdown && suggestions.length > 0 && (
            <ul className="search-dropdown">
              {suggestions.map((s) => (
                <li key={s.scripCode} onMouseDown={() => handleSuggestionClick(s.symbolRoot || s.name)}>
                  <span className="sd-symbol">{s.symbolRoot || s.name}</span>
                  <span className="sd-name">{s.fullName || s.name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="dashboard-content">
        {/* Watchlist Section */}
        <section className="watchlist-section">
          <h2>
            <FiStar /> Your Watchlist
            {watchlistLoading && <span style={{fontSize: '14px', marginLeft: '10px', color: '#666'}}>Loading...</span>}
          </h2>

          {watchlistError && (
            <div style={{padding: '15px', backgroundColor: '#fee', color: '#c33', borderRadius: '8px', marginBottom: '15px'}}>
              {watchlistError}
            </div>
          )}

          {watchlistLoading ? (
            <div className="stocks-grid">
              {[1, 2, 3, 4, 5, 6].map(i => (
                <div key={i} className="stock-card loading-card">
                  <div className="loading-placeholder"></div>
                </div>
              ))}
            </div>
          ) : (
            <div className="stocks-grid">
              {watchlistStocks.length === 0 && (
                <p style={{ color: '#a0a0b0' }}>
                  Your watchlist is empty. Open a stock and click "Add to Watchlist".
                </p>
              )}

              {watchlistStocks.map((stock) => (
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
                    <span className="stock-price">{stock.price != null ? `₹${stock.price.toFixed(2)}` : 'N/A'}</span>
                    {stock.changePercent != null && (
                      <span className={`stock-change ${stock.change >= 0 ? 'positive' : 'negative'}`}>
                        {stock.change >= 0 ? <FiTrendingUp /> : <FiTrendingDown />}
                        {stock.change >= 0 ? '+' : ''}{stock.changePercent?.toFixed(2)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Market News Section */}
        <section className="news-section">
          <h2>
            <FiClock /> Latest Market News
            {newsLoading && <span style={{fontSize: '14px', marginLeft: '10px', color: '#666'}}>Loading...</span>}
          </h2>
          
          {newsError && (
            <div style={{padding: '15px', backgroundColor: '#fee', color: '#c33', borderRadius: '8px', marginBottom: '15px'}}>
              {newsError}
              <button onClick={loadNews} style={{marginLeft: '10px', padding: '5px 10px', cursor: 'pointer'}}>
                Retry
              </button>
            </div>
          )}
          
          <div className="news-list">
            {newsItems.length === 0 && !newsLoading && !newsError && (
              <p style={{textAlign: 'center', color: '#666', padding: '20px'}}>
                No news available at the moment.
              </p>
            )}
            
            {newsItems.map((news) => (
              <article key={news.id} className="news-card" onClick={() => news.url && window.open(news.url, '_blank')}>
                <div className="news-content">
                  <span className="news-category">{news.category}</span>
                  <h3>{news.title}</h3>
                  {news.description && (
                    <p style={{fontSize: '14px', color: '#666', marginTop: '5px'}}>{news.description.substring(0, 150)}...</p>
                  )}
                  <div className="news-meta">
                    <span className="news-source">{news.source}</span>
                    <span className="news-time">{news.time}</span>
                    {news.sentiment && (
                      <span style={{
                        marginLeft: '10px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        backgroundColor: news.sentiment.label === 'Bullish' ? '#d4edda' : '#f8d7da',
                        color: news.sentiment.label === 'Bullish' ? '#155724' : '#721c24'
                      }}>
                        {news.sentiment.label}
                      </span>
                    )}
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
