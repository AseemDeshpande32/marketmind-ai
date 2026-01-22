import { Link } from 'react-router-dom'
import { FiTrendingUp, FiMessageSquare, FiPieChart, FiShield, FiArrowRight } from 'react-icons/fi'
import Navbar from '../components/Navbar'
import './LandingPage.css'

const LandingPage = () => {
  const features = [
    {
      icon: <FiTrendingUp />,
      title: 'AI-Powered Analysis',
      description: 'Get intelligent insights and predictions powered by advanced machine learning algorithms.'
    },
    {
      icon: <FiMessageSquare />,
      title: 'Smart Chatbot',
      description: 'Ask questions about stocks, markets, and investments in natural language.'
    },
    {
      icon: <FiPieChart />,
      title: 'Real-time Data',
      description: 'Access live market data, news, and comprehensive stock information.'
    },
    {
      icon: <FiShield />,
      title: 'Secure & Private',
      description: 'Your financial data is encrypted and protected with enterprise-grade security.'
    }
  ]

  return (
    <div className="landing-page">
      <Navbar />
      
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <h1 className="hero-title">
            Invest Smarter with
            <span className="gradient-text"> AI-Powered Insights</span>
          </h1>
          <p className="hero-subtitle">
            MarketMind AI helps you make informed investment decisions with real-time analysis,
            personalized recommendations, and an intelligent chatbot assistant.
          </p>
          <div className="hero-buttons">
            <Link to="/register" className="btn-primary">
              Start Free Trial
              <FiArrowRight />
            </Link>
            <Link to="/login" className="btn-secondary">
              Sign In
            </Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="hero-card">
            <div className="stock-preview">
              <div className="stock-header">
                <span className="stock-symbol">AAPL</span>
                <span className="stock-change positive">+2.45%</span>
              </div>
              <div className="stock-price">$178.52</div>
              <div className="stock-graph">
                <svg viewBox="0 0 100 40" className="graph-line">
                  <polyline
                    points="0,35 15,30 30,32 45,20 60,25 75,15 100,10"
                    fill="none"
                    stroke="url(#gradient)"
                    strokeWidth="2"
                  />
                  <defs>
                    <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#00d4ff" />
                      <stop offset="100%" stopColor="#7c3aed" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features" id="features">
        <h2 className="section-title">Why Choose MarketMind?</h2>
        <div className="features-grid">
          {features.map((feature, index) => (
            <div key={index} className="feature-card">
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta">
        <div className="cta-content">
          <h2>Ready to Transform Your Investment Strategy?</h2>
          <p>Join thousands of investors who trust MarketMind AI for smarter decisions.</p>
          <Link to="/register" className="btn-primary">
            Get Started Now
            <FiArrowRight />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-brand">
            <FiTrendingUp className="footer-logo" />
            <span>MarketMind AI</span>
          </div>
          <p>&copy; 2026 MarketMind AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
