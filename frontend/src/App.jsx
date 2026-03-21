import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { initializeTheme } from './services/settingsService'
import { isAuthenticated } from './services/authService'
import LandingPage from './pages/LandingPage'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import StockDetails from './pages/StockDetails'
import Chatbot from './pages/Chatbot'
import Profile from './pages/Profile'
import About from './pages/About'
import PublicAbout from './pages/PublicAbout'
import Terms from './pages/Terms'
import Layout from './components/Layout'
import './App.css'

// Protected Route Component
function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return children
}

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
        <Route path="/public-about" element={<PublicAbout />} />
        <Route path="/terms" element={<Terms />} />
        
        {/* Protected Routes with Sidebar */}
        <Route path="/dashboard" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
        <Route path="/stock/:symbol" element={<ProtectedRoute><Layout><StockDetails /></Layout></ProtectedRoute>} />
        <Route path="/chatbot" element={<ProtectedRoute><Layout><Chatbot /></Layout></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Layout><Profile /></Layout></ProtectedRoute>} />
        <Route path="/about" element={<ProtectedRoute><Layout><About /></Layout></ProtectedRoute>} />
      </Routes>
    </Router>
  )
}

export default App
