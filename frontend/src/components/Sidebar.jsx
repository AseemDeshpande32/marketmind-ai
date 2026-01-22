import { NavLink } from 'react-router-dom'
import { FiHome, FiMessageSquare, FiUser, FiInfo, FiLogOut, FiTrendingUp } from 'react-icons/fi'
import './Sidebar.css'

const Sidebar = () => {
  const menuItems = [
    { path: '/dashboard', icon: <FiHome />, label: 'Home' },
    { path: '/chatbot', icon: <FiMessageSquare />, label: 'AI Chatbot' },
    { path: '/profile', icon: <FiUser />, label: 'Profile' },
    { path: '/about', icon: <FiInfo />, label: 'About' },
  ]

  const handleLogout = () => {
    // Add logout logic here
    window.location.href = '/'
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <FiTrendingUp className="logo-icon" />
        <span className="logo-text">MarketMind</span>
      </div>
      
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      
      <div className="sidebar-footer">
        <button className="logout-btn" onClick={handleLogout}>
          <FiLogOut />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  )
}

export default Sidebar
