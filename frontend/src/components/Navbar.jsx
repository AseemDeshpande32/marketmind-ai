import { Link } from 'react-router-dom'
import { FiTrendingUp } from 'react-icons/fi'
import './Navbar.css'

const Navbar = () => {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          <FiTrendingUp className="navbar-logo-icon" />
          <span>MarketMind AI</span>
        </Link>
        
        <div className="navbar-links">
          <a href="#features">Features</a>
          <a href="#about">About</a>
          <a href="#contact">Contact</a>
        </div>
        
        <div className="navbar-auth">
          <Link to="/login" className="btn-login">Login</Link>
          <Link to="/register" className="btn-register">Get Started</Link>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
