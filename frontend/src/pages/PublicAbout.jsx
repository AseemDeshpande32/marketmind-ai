import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FiTarget, FiUsers, FiShield, FiAward, FiArrowRight } from 'react-icons/fi'
import Navbar from '../components/Navbar'
import './About.css'

const PublicAbout = () => {
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [])

  const features = [
    {
      icon: <FiTarget />,
      title: 'Our Mission',
      description: 'To democratize investment intelligence by making AI-powered financial insights accessible to everyone, from beginners to experienced investors.'
    },
    {
      icon: <FiUsers />,
      title: 'Built for Investors',
      description: 'Designed with real investor needs in mind, our platform combines powerful analytics with an intuitive interface for seamless decision-making.'
    },
    {
      icon: <FiShield />,
      title: 'Security First',
      description: 'Your data security is our priority. We employ enterprise-grade encryption and never share your personal information with third parties.'
    },
    {
      icon: <FiAward />,
      title: 'Cutting-Edge AI',
      description: 'Leveraging the latest advances in machine learning and natural language processing to deliver accurate, actionable market insights.'
    }
  ]

  return (
    <>
      <Navbar />
      <div className="about-page">
        <div className="about-hero">
          <h1>About MarketMind AI</h1>
          <p>
            An intelligent investment assistant powered by artificial intelligence,
            designed to help you make smarter financial decisions.
          </p>
        </div>

        <section className="about-section">
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

        <section className="about-section project-info">
          <h2>About This Project</h2>
          <div className="project-content">
            <p>
              MarketMind AI is a final year capstone project that demonstrates the integration of
              artificial intelligence with financial technology. The platform provides users with:
            </p>
            <ul>
              <li>Real-time stock market data and analysis</li>
              <li>AI-powered chatbot for investment queries</li>
              <li>Personalized investment insights and recommendations</li>
              <li>Comprehensive market news aggregation</li>
              <li>User-friendly dashboard for portfolio tracking</li>
            </ul>
          </div>
        </section>

        <section className="about-section disclaimer">
          <h2>Disclaimer</h2>
          <div className="disclaimer-content">
            <p>
              <strong>Educational Project:</strong> MarketMind AI is developed as an academic project
              and is intended for educational and demonstration purposes only.
            </p>
            <p>
              <strong>Not Financial Advice:</strong> The information provided by this platform should
              not be considered as financial advice. Always consult with a qualified financial advisor
              before making investment decisions.
            </p>
            <p>
              <strong>Data Accuracy:</strong> While we strive to provide accurate information, we cannot
              guarantee the accuracy, completeness, or timeliness of the data displayed.
            </p>
          </div>
        </section>

        <section className="about-section cta-section">
          <h2>Get Started Today</h2>
          <p>Join us and start making smarter investment decisions with AI-powered insights.</p>
          <div className="cta-buttons">
            <Link to="/register" className="btn-primary">
              Sign Up <FiArrowRight />
            </Link>
            <Link to="/login" className="btn-secondary">
              Login
            </Link>
          </div>
        </section>
      </div>
    </>
  )
}

export default PublicAbout
