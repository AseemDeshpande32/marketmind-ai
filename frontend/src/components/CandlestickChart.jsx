import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart } from 'lightweight-charts';
import { io } from 'socket.io-client';
import API_BASE_URL from '../config/api';
import './CandlestickChart.css';

const INTERVALS = ['1m', '5m', '15m', '30m', '1H', '1D'];

/**
 * CandlestickChart
 *
 * Renders a lightweight-charts candlestick chart fed with 5paisa historical data.
 *
 * Props:
 *   scripCode  {number}  - 5paisa scrip code
 *   exchange   {string}  - "N" (NSE) or "B" (BSE)
 *   symbol     {string}  - display name, e.g. "TCS"
 */
export default function CandlestickChart({ scripCode, exchange = 'N', symbol = '' }) {
  const containerRef = useRef(null);
  const chartRef     = useRef(null);
  const seriesRef    = useRef(null);

  const [interval,    setActiveInterval]    = useState('1D');
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // ── fetch candles ──────────────────────────────────────────────────────────
  const fetchCandles = useCallback(async () => {
    if (!scripCode) return;
    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE_URL}/stocks/5paisa/historical/${scripCode}` +
                  `?exchange=${exchange}&interval=${interval}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const json = await res.json();
      const candles = (json.candles || []).map((c) => ({
        time:  c.time,          // ISO or UNIX timestamp
        open:  parseFloat(c.open),
        high:  parseFloat(c.high),
        low:   parseFloat(c.low),
        close: parseFloat(c.close),
      }));

      if (seriesRef.current && candles.length) {
        seriesRef.current.setData(candles);
        chartRef.current?.timeScale().fitContent();
      }
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) {
      console.error('CandlestickChart fetch error:', e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [scripCode, exchange, interval]);

  // ── create/destroy chart ───────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: 380,
      layout: {
        background:  { color: '#0a0a14' },
        textColor:   '#a0a0b0',
      },
      grid: {
        vertLines:   { color: '#1a1a2e' },
        horzLines:   { color: '#1a1a2e' },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#2a2a3e' },
      timeScale: {
        borderColor:      '#2a2a3e',
        timeVisible:      true,
        secondsVisible:   false,
      },
    });

    const series = chart.addCandlestickSeries({
      upColor:        '#26a69a',
      downColor:      '#ef5350',
      borderVisible:   false,
      wickUpColor:    '#26a69a',
      wickDownColor:  '#ef5350',
    });

    chartRef.current  = chart;
    seriesRef.current = series;

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current  = null;
      seriesRef.current = null;
    };
  }, []);

  // ── (re)fetch when interval or scripCode changes ───────────────────────────
  useEffect(() => { fetchCandles(); }, [fetchCandles]);

  // ── WebSocket for real-time candle updates ─────────────────────────────────
  useEffect(() => {
    if (!scripCode || interval !==  '1D') {
      // Only enable live updates for 1D interval (intraday)
      return;
    }

    const WS_URL = API_BASE_URL.replace('/api', '').replace('http', 'ws');
    const socket = io(WS_URL, {
      transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
      console.log('[Chart WS] Connected');
      // Subscribe to live updates
      socket.emit('subscribe_stock', {
        scrip_code: scripCode,
        exchange: exchange,
        exchange_type: 'C'
      });
    });

    socket.on('candle_update', (data) => {
      // Only process updates for current scrip
      if (data.scrip_code !== scripCode) return;
      
      // Update the chart with new candle data
      if (seriesRef.current) {
        try {
          seriesRef.current.update({
            time: data.time,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close
          });
          setLastUpdated(new Date().toLocaleTimeString());
        } catch (err) {
          console.error('[Chart WS] Update error:', err);
        }
      }
    });

    socket.on('disconnect', () => {
      console.log('[Chart WS] Disconnected');
    });

    return () => {
      if (scripCode) {
        socket.emit('unsubscribe_stock', { scrip_code: scripCode });
      }
      socket.disconnect();
    };
  }, [scripCode, exchange, interval]);

  return (
    <div className="candlestick-chart-wrapper">
      {/* Header */}
      <div className="chart-header">
        <div className="chart-title">
          {symbol && <span className="chart-symbol">{symbol}</span>}
          <span className="chart-label"> Price Chart</span>
          {lastUpdated && (
            <span className="chart-updated">Updated {lastUpdated}</span>
          )}
        </div>

        {/* Interval buttons */}
        <div className="chart-intervals">
          {INTERVALS.map((iv) => (
            <button
              key={iv}
              className={`interval-btn ${interval === iv ? 'active' : ''}`}
              onClick={() => setActiveInterval(iv)}
            >
              {iv}
            </button>
          ))}
        </div>
      </div>

      {/* Chart container */}
      <div className="chart-body" style={{ position: 'relative' }}>
        {loading && (
          <div className="chart-overlay">
            <div className="chart-spinner" />
            <span>Loading chart…</span>
          </div>
        )}
        {error && !loading && (
          <div className="chart-overlay chart-error">
            <span>⚠ {error}</span>
            <button className="retry-btn" onClick={fetchCandles}>Retry</button>
          </div>
        )}
        <div ref={containerRef} className="lw-chart-container" />
      </div>
    </div>
  );
}
