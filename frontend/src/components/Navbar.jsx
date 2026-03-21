import { Link, useLocation, useNavigate } from 'react-router-dom'
import { FiTrendingUp } from 'react-icons/fi'
import './Navbar.css'

const Navbar = () => {
  const location = useLocation()
  const navigate = useNavigate()
  
  const handleNavClick = (sectionId) => {
    if (location.pathname === '/') {
      // Already on landing page, just scroll to section
      const element = document.getElementById(sectionId)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' })
      }
    } else {
      // Not on landing page, navigate to home with hash
      navigate(`/#${sectionId}`)
    }
  }

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          <FiTrendingUp className="navbar-logo-icon" />
          <span>MarketMind AI</span>
        </Link>
        
        <div className="navbar-links">
          <button onClick={() => handleNavClick('features')} className="nav-button">Features</button>
          <Link to="/public-about" onClick={() => window.scrollTo({ top: 0, behavior: 'auto' })}>About</Link>
          <button onClick={() => handleNavClick('contact')} className="nav-button">Contact</button>
        </div>
        
        <div className="navbar-auth">
          <Link to="/login" className="btn-login">Login</Link>
          <Link to="/register" className="btn-register">Sign Up</Link>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
