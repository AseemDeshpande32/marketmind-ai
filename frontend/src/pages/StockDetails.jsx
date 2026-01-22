import { useParams, useNavigate } from 'react-router-dom'
import { FiArrowLeft, FiTrendingUp, FiTrendingDown, FiDollarSign, FiBarChart2, FiActivity } from 'react-icons/fi'
import './StockDetails.css'

const StockDetails = () => {
  const { symbol } = useParams()
  const navigate = useNavigate()

  // Mock data - replace with real API data
  const stockData = {
    symbol: symbol?.toUpperCase() || 'AAPL',
    name: 'Apple Inc.',
    price: 178.52,
    change: 2.45,
    changePercent: 1.39,
    isUp: true,
    open: 176.15,
    high: 179.63,
    low: 175.82,
    volume: '52.3M',
    marketCap: '2.78T',
    peRatio: 28.45,
    dividend: 0.96,
    week52High: 199.62,
    week52Low: 164.08,
    avgVolume: '58.2M',
    beta: 1.28
  }

  const aiInsights = [
    {
      type: 'positive',
      title: 'Strong Revenue Growth',
      description: 'Company reported 12% YoY revenue growth in the latest quarter, exceeding analyst expectations.'
    },
    {
      type: 'positive',
      title: 'Expanding Services Segment',
      description: 'Services revenue continues to grow, providing a stable recurring income stream.'
    },
    {
      type: 'neutral',
      title: 'Market Position',
      description: 'Maintains dominant position in premium smartphone market despite increased competition.'
    },
    {
      type: 'negative',
      title: 'Supply Chain Concerns',
      description: 'Ongoing geopolitical tensions may impact supply chain and production capacity.'
    }
  ]

  return (
    <div className="stock-details">
      <button className="back-button" onClick={() => navigate('/dashboard')}>
        <FiArrowLeft /> Back to Dashboard
      </button>

      <div className="stock-header">
        <div className="stock-title">
          <h1>{stockData.symbol}</h1>
          <span className="company-name">{stockData.name}</span>
        </div>
        <div className="stock-price-section">
          <span className="current-price">${stockData.price.toFixed(2)}</span>
          <span className={`price-change ${stockData.isUp ? 'positive' : 'negative'}`}>
            {stockData.isUp ? <FiTrendingUp /> : <FiTrendingDown />}
            {stockData.isUp ? '+' : ''}${stockData.change.toFixed(2)} ({stockData.changePercent.toFixed(2)}%)
          </span>
        </div>
      </div>

      <div className="stock-content">
        {/* Price Chart Placeholder */}
        <div className="chart-section">
          <h2><FiActivity /> Price Chart</h2>
          <div className="chart-placeholder">
            <svg viewBox="0 0 400 150" className="stock-chart">
              <defs>
                <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="rgba(0, 212, 255, 0.3)" />
                  <stop offset="100%" stopColor="rgba(0, 212, 255, 0)" />
                </linearGradient>
              </defs>
              <path
                d="M0,100 L30,90 L60,95 L90,70 L120,75 L150,50 L180,60 L210,40 L240,45 L270,30 L300,35 L330,20 L360,25 L400,15"
                fill="none"
                stroke="url(#lineGradient)"
                strokeWidth="3"
              />
              <defs>
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#00d4ff" />
                  <stop offset="100%" stopColor="#7c3aed" />
                </linearGradient>
              </defs>
              <path
                d="M0,100 L30,90 L60,95 L90,70 L120,75 L150,50 L180,60 L210,40 L240,45 L270,30 L300,35 L330,20 L360,25 L400,15 L400,150 L0,150 Z"
                fill="url(#chartGradient)"
              />
            </svg>
            <div className="chart-timeframes">
              <button className="active">1D</button>
              <button>1W</button>
              <button>1M</button>
              <button>3M</button>
              <button>1Y</button>
              <button>5Y</button>
            </div>
          </div>
        </div>

        {/* Key Statistics */}
        <div className="stats-section">
          <h2><FiBarChart2 /> Key Statistics</h2>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Open</span>
              <span className="stat-value">${stockData.open}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">High</span>
              <span className="stat-value">${stockData.high}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Low</span>
              <span className="stat-value">${stockData.low}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Volume</span>
              <span className="stat-value">{stockData.volume}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Market Cap</span>
              <span className="stat-value">${stockData.marketCap}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">P/E Ratio</span>
              <span className="stat-value">{stockData.peRatio}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">52W High</span>
              <span className="stat-value">${stockData.week52High}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">52W Low</span>
              <span className="stat-value">${stockData.week52Low}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Avg Volume</span>
              <span className="stat-value">{stockData.avgVolume}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Beta</span>
              <span className="stat-value">{stockData.beta}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Dividend</span>
              <span className="stat-value">${stockData.dividend}</span>
            </div>
          </div>
        </div>

        {/* AI Insights */}
        <div className="insights-section">
          <h2><FiDollarSign /> AI Insights</h2>
          <div className="insights-list">
            {aiInsights.map((insight, index) => (
              <div key={index} className={`insight-card ${insight.type}`}>
                <h3>{insight.title}</h3>
                <p>{insight.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default StockDetails
