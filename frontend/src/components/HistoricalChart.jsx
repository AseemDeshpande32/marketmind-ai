import { useState, useEffect } from 'react'
import { 
  ResponsiveContainer, 
  ComposedChart, 
  Line, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from 'recharts'
import './HistoricalChart.css'

const HistoricalChart = ({ scripCode, exchange = 'N', timeRange = '1M' }) => {
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Calculate date range based on timeRange parameter
  const getDateRange = (range) => {
    const toDate = new Date()
    const fromDate = new Date()
    
    switch(range) {
      case '1W':
        fromDate.setDate(toDate.getDate() - 7)
        break
      case '1M':
        fromDate.setMonth(toDate.getMonth() - 1)
        break
      case '3M':
        fromDate.setMonth(toDate.getMonth() - 3)
        break
      case '6M':
        fromDate.setMonth(toDate.getMonth() - 6)
        break
      case '1Y':
        fromDate.setFullYear(toDate.getFullYear() - 1)
        break
      default:
        fromDate.setMonth(toDate.getMonth() - 1)
    }
    
    return {
      from: fromDate.toISOString().split('T')[0],
      to: toDate.toISOString().split('T')[0]
    }
  }

  useEffect(() => {
    const fetchHistoricalData = async () => {
      if (!scripCode) return

      try {
        setLoading(true)
        setError(null)
        
        const { from, to } = getDateRange(timeRange)
        const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:5000/api').replace(/\/api$/, '')
        const url = `${apiUrl}/api/stocks/5paisa/historical/${scripCode}?exchange=${exchange}&from_date=${from}&to_date=${to}`
        
        console.log('📊 Fetching historical data:', url)
        
        const response = await fetch(url)
        
        if (!response.ok) {
          throw new Error(`Failed to fetch historical data: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        if (data.error) {
          throw new Error(data.message || 'Failed to fetch historical data')
        }
        
        // Format data for recharts
        const formattedData = data.candles.map(candle => ({
          date: new Date(candle.date).toLocaleDateString('en-IN', { 
            day: '2-digit', 
            month: 'short' 
          }),
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          volume: candle.volume
        }))
        
        setChartData(formattedData)
      } catch (err) {
        console.error('Error fetching historical data:', err)
        setError(err.message || 'Failed to load chart data')
      } finally {
        setLoading(false)
      }
    }

    fetchHistoricalData()
  }, [scripCode, exchange, timeRange])

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-date">{payload[0].payload.date}</p>
          <p className="tooltip-item">
            <span className="tooltip-label">Open:</span>
            <span className="tooltip-value">₹{payload[0].payload.open.toFixed(2)}</span>
          </p>
          <p className="tooltip-item">
            <span className="tooltip-label">High:</span>
            <span className="tooltip-value high">₹{payload[0].payload.high.toFixed(2)}</span>
          </p>
          <p className="tooltip-item">
            <span className="tooltip-label">Low:</span>
            <span className="tooltip-value low">₹{payload[0].payload.low.toFixed(2)}</span>
          </p>
          <p className="tooltip-item">
            <span className="tooltip-label">Close:</span>
            <span className="tooltip-value">₹{payload[0].payload.close.toFixed(2)}</span>
          </p>
          <p className="tooltip-item">
            <span className="tooltip-label">Volume:</span>
            <span className="tooltip-value">{payload[0].payload.volume.toLocaleString()}</span>
          </p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className="chart-loading">
        <div className="spinner"></div>
        <p>Loading chart data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="chart-error">
        <p>⚠️ {error}</p>
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className="chart-error">
        <p>No data available for this time period</p>
      </div>
    )
  }

  return (
    <div className="historical-chart">
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
          <XAxis 
            dataKey="date" 
            stroke="#999"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#999"
            style={{ fontSize: '12px' }}
            domain={['dataMin - 10', 'dataMax + 10']}
            tickFormatter={(value) => `₹${value.toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />
          <Line 
            type="monotone" 
            dataKey="close" 
            stroke="#00d4ff" 
            strokeWidth={2}
            dot={false}
            name="Close Price"
            fill="url(#colorClose)"
          />
          <Bar 
            dataKey="volume" 
            fill="rgba(0, 212, 255, 0.2)" 
            yAxisId="volume"
            name="Volume"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export default HistoricalChart
