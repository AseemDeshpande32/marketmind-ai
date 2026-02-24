import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import { initializeTheme } from './services/settingsService'
import LandingPage from './pages/LandingPage'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import StockDetails from './pages/StockDetails'
import Chatbot from './pages/Chatbot'
import Profile from './pages/Profile'
import About from './pages/About'
import Layout from './components/Layout'
import './App.css'

function App() {
  // Initialize theme on app load
  useEffect(() => {
    initializeTheme()
  }, [])

  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Protected Routes with Sidebar */}
        <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
        <Route path="/stock/:symbol" element={<Layout><StockDetails /></Layout>} />
        <Route path="/chatbot" element={<Layout><Chatbot /></Layout>} />
        <Route path="/profile" element={<Layout><Profile /></Layout>} />
        <Route path="/about" element={<Layout><About /></Layout>} />
      </Routes>
    </Router>
  )
}

export default App
