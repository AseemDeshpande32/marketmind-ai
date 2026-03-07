/**
 * CandlestickChart — lightweight-charts v5 + 5paisa V2 historical API
 * Features: candlestick + volume, interval selector, auto-refresh during NSE market hours
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts'
import './CandlestickChart.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'

const INTERVALS = [
  { label: '1m',  value: '1m',  refreshSec: 60   },
  { label: '5m',  value: '5m',  refreshSec: 300  },
  { label: '15m', value: '15m', refreshSec: 900  },
  { label: '30m', value: '30m', refreshSec: 1800 },
  { label: '1H',  value: '60m', refreshSec: 3600 },
  { label: '1D',  value: '1d',  refreshSec: null  }, // no auto-refresh for daily
]

/** Returns true if NSE market is currently open (9:15–15:30 IST, Mon–Fri) */
const isMarketOpen = () => {
  const now  = new Date()
  const istMs = now.getTime() + (5.5 * 60 * 60 * 1000)
  const ist  = new Date(istMs)
  const day  = ist.getUTCDay()          // 0=Sun 6=Sat
  if (day === 0 || day === 6) return false
  const mins = ist.getUTCHours() * 60 + ist.getUTCMinutes()
  return mins >= 555 && mins <= 930     // 9:15 = 555, 15:30 = 930
}

const CandlestickChart = ({ scripCode, exchange = 'N', symbol = '' }) => {
  const containerRef   = useRef(null)
  const chartRef       = useRef(null)
  const candleRef      = useRef(null)
  const volumeRef      = useRef(null)
  const refreshTimer   = useRef(null)
  const countdownTimer = useRef(null)

  const [selectedInterval, setSelectedInterval] = useState('1d')
  const [loading,      setLoading]      = useState(false)
  const [error,        setError]        = useState(null)
  const [lastUpdated,  setLastUpdated]  = useState(null)
  const [marketOpen,   setMarketOpen]   = useState(false)
  const [countdown,    setCountdown]    = useState(null)

  // ── fetch candles ────────────────────────────────────────────────────────────
  const fetchCandles = useCallback(async (interval, showLoader = true) => {
    if (!scripCode) return
    if (showLoader) setLoading(true)
    setError(null)
    try {
      const res  = await fetch(
        `${API_BASE}/stocks/5paisa/historical/${scripCode}` +
        `?exchange=${exchange}&interval=${interval}`
      )
      const json = await res.json()
      if (!res.ok || json.error) throw new Error(json.message || 'Failed to fetch chart data')

      const candles = json.candles || []
      if (!candles.length) throw new Error('No candle data returned from 5paisa')

      const candleData = candles.map(c => ({
        time:  Math.floor(new Date(c.time).getTime() / 1000),
        open:  c.open, high: c.high, low: c.low, close: c.close,
      }))
      const volumeData = candles.map(c => ({
        time:  Math.floor(new Date(c.time).getTime() / 1000),
        value: c.volume,
        color: c.close >= c.open ? '#26a69a55' : '#ef535055',
      }))

      if (candleRef.current)  candleRef.current.setData(candleData)
      if (volumeRef.current)  volumeRef.current.setData(volumeData)
      if (chartRef.current)   chartRef.current.timeScale().fitContent()

      setLastUpdated(new Date())
      setMarketOpen(isMarketOpen())
    } catch (e) {
      setError(e.message)
    } finally {
      if (showLoader) setLoading(false)
    }
  }, [scripCode, exchange])

  // ── start / stop auto-refresh ─────────────────────────────────────────────
  const stopTimers = useCallback(() => {
    if (refreshTimer.current)   clearInterval(refreshTimer.current)
    if (countdownTimer.current) clearInterval(countdownTimer.current)
    refreshTimer.current   = null
    countdownTimer.current = null
    setCountdown(null)
  }, [])

  const startAutoRefresh = useCallback((interval) => {
    stopTimers()
    const cfg = INTERVALS.find(i => i.value === interval)
    if (!cfg?.refreshSec || !isMarketOpen()) return   // only intraday + market open

    let remaining = cfg.refreshSec
    setCountdown(remaining)

    countdownTimer.current = setInterval(() => {
      remaining -= 1
      setCountdown(remaining)
      if (remaining <= 0) remaining = cfg.refreshSec
    }, 1000)

    refreshTimer.current = setInterval(() => {
      fetchCandles(interval, false)   // silent re-fetch — no loading spinner
    }, cfg.refreshSec * 1000)
  }, [fetchCandles, stopTimers])

  // ── initialise chart once ──────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: 480,
      layout: {
        background: { color: '#0d1117' },
        textColor:  '#c9d1d9',
      },
      grid: {
        vertLines: { color: '#1e2a3a' },
        horzLines: { color: '#1e2a3a' },
      },
      crosshair:       { mode: 1 },
      rightPriceScale: { borderColor: '#1e2a3a' },
      timeScale: {
        borderColor:    '#1e2a3a',
        timeVisible:    true,
        secondsVisible: false,
      },
    })

    candleRef.current = chart.addSeries(CandlestickSeries, {
      upColor:       '#26a69a',
      downColor:     '#ef5350',
      borderVisible: false,
      wickUpColor:   '#26a69a',
      wickDownColor: '#ef5350',
    })

    volumeRef.current = chart.addSeries(HistogramSeries, {
      priceFormat:  { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    })

    chartRef.current = chart

    const ro = new ResizeObserver(entries => {
      chart.applyOptions({ width: entries[0].contentRect.width })
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
      stopTimers()
    }
  }, [stopTimers])

  // ── reload + restart refresh when interval / scripCode changes ───────────────
  useEffect(() => {
    fetchCandles(selectedInterval, true)
    startAutoRefresh(selectedInterval)
    return () => stopTimers()
  }, [selectedInterval, scripCode, exchange, fetchCandles, startAutoRefresh, stopTimers])

  if (!scripCode) {
    return (
      <div className="cc-unavailable">
        📊 Chart unavailable — scrip code not found for this symbol.
      </div>
    )
  }

  return (
    <div className="cc-wrapper">
      {/* ── header ── */}
      <div className="cc-header">
        <div className="cc-title-row">
          {symbol && <span className="cc-symbol">{symbol}</span>}
          <div className="cc-status-row">
            {marketOpen ? (
              <span className="cc-live-badge">
                <span className="cc-live-dot" />
                LIVE
                {countdown !== null && (
                  <span className="cc-countdown"> · refresh in {countdown}s</span>
                )}
              </span>
            ) : (
              <span className="cc-closed-badge">Market Closed</span>
            )}
            {lastUpdated && (
              <span className="cc-updated">
                Updated {lastUpdated.toLocaleTimeString('en-IN')}
              </span>
            )}
          </div>
        </div>

        <div className="cc-intervals">
          {INTERVALS.map(i => (
            <button
              key={i.value}
              className={`cc-interval-btn ${selectedInterval === i.value ? 'active' : ''}`}
              onClick={() => setSelectedInterval(i.value)}
            >
              {i.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── chart area ── */}
      <div className="cc-chart-area">
        {loading && (
          <div className="cc-overlay">
            <div className="cc-spinner" />
            <span>Loading chart data…</span>
          </div>
        )}
        {error && !loading && (
          <div className="cc-overlay cc-error">
            <span>⚠️ {error}</span>
            <button className="cc-retry-btn" onClick={() => fetchCandles(selectedInterval, true)}>Retry</button>
          </div>
        )}
        <div ref={containerRef} className="cc-canvas" />
      </div>
    </div>
  )
}

export default CandlestickChart
