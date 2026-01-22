import { useState, useEffect } from 'react'
import { FiUser, FiMail, FiPhone, FiMapPin, FiEdit2, FiSave, FiCamera, FiSettings, FiMoon, FiSun } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import { getCurrentUser, removeAuthToken } from '../services/authService'
import { changePassword, deleteAccount, getTheme, setTheme } from '../services/settingsService'
import './Profile.css'

const Profile = () => {
  const navigate = useNavigate()
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [currentTheme, setCurrentTheme] = useState(getTheme())
  
  // Modal states
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  
  // Password change form
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')
  
  // Delete account form
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteError, setDeleteError] = useState('')
  
  const [profile, setProfile] = useState({
    fullName: '',
    email: '',
    phone: '',
    location: '',
    bio: '',
    investmentStyle: 'Growth',
    riskTolerance: 'Moderate',
    experience: '3-5 years',
    memberSince: ''
  })

  const [editedProfile, setEditedProfile] = useState(profile)

  // Fetch user data on component mount
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setLoading(true)
        const result = await getCurrentUser()
        
        if (result.success) {
          const userData = result.data
          const userProfile = {
            fullName: userData.name || '',
            email: userData.email || '',
            phone: userData.phone || '',
            location: userData.location || '',
            bio: userData.bio || 'Passionate investor building wealth through smart, data-driven investment decisions.',
            investmentStyle: userData.investmentStyle || 'Growth',
            riskTolerance: userData.riskTolerance || 'Moderate',
            experience: userData.experience || '3-5 years',
            memberSince: userData.created_at ? new Date(userData.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'Jan 2024'
          }
          setProfile(userProfile)
          setEditedProfile(userProfile)
        }
      } catch (error) {
        console.error('Failed to fetch user data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchUserData()
  }, [])

  const handleChange = (e) => {
    setEditedProfile({
      ...editedProfile,
      [e.target.name]: e.target.value
    })
  }

  const handleSave = () => {
    setProfile(editedProfile)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditedProfile(profile)
    setIsEditing(false)
  }

  // Theme toggle handler
  const toggleTheme = () => {
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    setCurrentTheme(newTheme)
    // Force a re-render by updating the document attribute
    document.documentElement.setAttribute('data-theme', newTheme)
  }

  // Password change handlers
  const handlePasswordChange = (e) => {
    setPasswordForm({
      ...passwordForm,
      [e.target.name]: e.target.value
    })
    setPasswordError('')
  }

  const handlePasswordSubmit = async (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')

    // Validate passwords match
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('New passwords do not match')
      return
    }

    // Validate password length
    if (passwordForm.newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters')
      return
    }

    const result = await changePassword(passwordForm.currentPassword, passwordForm.newPassword)

    if (result.success) {
      setPasswordSuccess('Password changed successfully!')
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
      setTimeout(() => {
        setShowPasswordModal(false)
        setPasswordSuccess('')
      }, 2000)
    } else {
      setPasswordError(result.error)
    }
  }

  // Delete account handlers
  const handleDeleteAccount = async (e) => {
    e.preventDefault()
    setDeleteError('')

    if (!deletePassword) {
      setDeleteError('Please enter your password')
      return
    }

    const result = await deleteAccount(deletePassword)

    if (result.success) {
      // Clear auth and redirect to login
      removeAuthToken()
      navigate('/login')
    } else {
      setDeleteError(result.error)
    }
  }

  return (
    <div className="profile-page">
      <div className="profile-header">
        <h1>My Profile</h1>
        <div className="header-actions">
          <button className="settings-btn" onClick={() => setShowSettings(!showSettings)}>
            <FiSettings /> Settings
          </button>
          {!isEditing ? (
            <button className="edit-btn" onClick={() => setIsEditing(true)}>
              <FiEdit2 /> Edit Profile
            </button>
          ) : (
            <div className="edit-actions">
              <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
              <button className="save-btn" onClick={handleSave}>
                <FiSave /> Save Changes
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="settings-modal" onClick={() => setShowSettings(false)}>
          <div className="settings-content" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <h2>Settings</h2>
              <button className="close-btn" onClick={() => setShowSettings(false)}>×</button>
            </div>
            <div className="settings-body">
              <div className="setting-item">
                <h3>Account Settings</h3>
                <button className="setting-option" onClick={() => {
                  setShowPasswordModal(true)
                  setShowSettings(false)
                }}>
                  Change Password
                </button>
              </div>
              <div className="setting-item">
                <h3>Application</h3>
                <button className="setting-option theme-toggle" onClick={toggleTheme}>
                  {currentTheme === 'dark' ? <FiSun /> : <FiMoon />}
                  <span>{currentTheme === 'dark' ? ' Switch to Light Mode' : ' Switch to Dark Mode'}</span>
                </button>
              </div>
              <div className="setting-item danger-zone">
                <h3>Danger Zone</h3>
                <button className="setting-option danger" onClick={() => {
                  setShowDeleteModal(true)
                  setShowSettings(false)
                }}>
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="settings-modal" onClick={() => setShowPasswordModal(false)}>
          <div className="settings-content" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <h2>Change Password</h2>
              <button className="close-btn" onClick={() => setShowPasswordModal(false)}>×</button>
            </div>
            <div className="settings-body">
              <form onSubmit={handlePasswordSubmit}>
                <div className="form-group">
                  <label>Current Password</label>
                  <input
                    type="password"
                    name="currentPassword"
                    value={passwordForm.currentPassword}
                    onChange={handlePasswordChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>New Password</label>
                  <input
                    type="password"
                    name="newPassword"
                    value={passwordForm.newPassword}
                    onChange={handlePasswordChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Confirm New Password</label>
                  <input
                    type="password"
                    name="confirmPassword"
                    value={passwordForm.confirmPassword}
                    onChange={handlePasswordChange}
                    required
                  />
                </div>
                {passwordError && <div className="error-message">{passwordError}</div>}
                {passwordSuccess && <div className="success-message">{passwordSuccess}</div>}
                <div className="modal-actions">
                  <button type="button" className="cancel-btn" onClick={() => setShowPasswordModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="save-btn">
                    Change Password
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Delete Account Modal */}
      {showDeleteModal && (
        <div className="settings-modal" onClick={() => setShowDeleteModal(false)}>
          <div className="settings-content" onClick={(e) => e.stopPropagation()}>
            <div className="settings-header">
              <h2>Delete Account</h2>
              <button className="close-btn" onClick={() => setShowDeleteModal(false)}>×</button>
            </div>
            <div className="settings-body">
              <div className="warning-box">
                <h3>⚠️ Warning</h3>
                <p>This action cannot be undone. All your data will be permanently deleted.</p>
              </div>
              <form onSubmit={handleDeleteAccount}>
                <div className="form-group">
                  <label>Enter your password to confirm</label>
                  <input
                    type="password"
                    value={deletePassword}
                    onChange={(e) => {
                      setDeletePassword(e.target.value)
                      setDeleteError('')
                    }}
                    required
                  />
                </div>
                {deleteError && <div className="error-message">{deleteError}</div>}
                <div className="modal-actions">
                  <button type="button" className="cancel-btn" onClick={() => setShowDeleteModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="delete-btn">
                    Delete My Account
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading profile...</p>
        </div>
      ) : null}

      {!loading && (
        <div className="profile-content">
          <div className="profile-card main-info">
            <div className="avatar-section">
              <div className="avatar">
                <span>{profile.fullName ? profile.fullName.split(' ').map(n => n[0]).join('').toUpperCase() : 'U'}</span>
                {isEditing && (
                  <button className="avatar-edit">
                    <FiCamera />
                  </button>
                )}
              </div>
              <div className="user-name">
                <h2>{profile.fullName || 'User'}</h2>
                <span className="member-since">Member since {profile.memberSince}</span>
              </div>
            </div>

            <div className="info-grid">
              <div className="info-item">
                <FiUser className="info-icon" />
                <div className="info-content">
                  <label>Full Name</label>
                  {isEditing ? (
                    <input
                      type="text"
                      name="fullName"
                      value={editedProfile.fullName}
                      onChange={handleChange}
                    />
                  ) : (
                    <span>{profile.fullName}</span>
                  )}
                </div>
              </div>

              <div className="info-item">
                <FiMail className="info-icon" />
                <div className="info-content">
                  <label>Email Address</label>
                  {isEditing ? (
                    <input
                      type="email"
                      name="email"
                      value={editedProfile.email}
                      onChange={handleChange}
                    />
                  ) : (
                    <span>{profile.email}</span>
                  )}
                </div>
              </div>

              <div className="info-item">
                <FiPhone className="info-icon" />
                <div className="info-content">
                  <label>Phone Number</label>
                  {isEditing ? (
                    <input
                      type="tel"
                      name="phone"
                      value={editedProfile.phone}
                      onChange={handleChange}
                    />
                  ) : (
                    <span>{profile.phone}</span>
                  )}
                </div>
              </div>

              <div className="info-item">
                <FiMapPin className="info-icon" />
                <div className="info-content">
                  <label>Location</label>
                  {isEditing ? (
                    <input
                      type="text"
                      name="location"
                      value={editedProfile.location}
                      onChange={handleChange}
                    />
                  ) : (
                    <span>{profile.location}</span>
                  )}
                </div>
              </div>
            </div>

            <div className="bio-section">
              <label>Bio</label>
              {isEditing ? (
                <textarea
                  name="bio"
                  value={editedProfile.bio}
                  onChange={handleChange}
                  rows={3}
                />
              ) : (
                <p>{profile.bio}</p>
              )}
            </div>
          </div>

          <div className="profile-card investment-profile">
            <h3>Investment Profile</h3>
            <div className="investment-options">
              <div className="option-group">
                <label>Investment Style</label>
                {isEditing ? (
                  <select
                    name="investmentStyle"
                    value={editedProfile.investmentStyle}
                    onChange={handleChange}
                  >
                    <option value="Conservative">Conservative</option>
                    <option value="Growth">Growth</option>
                    <option value="Aggressive">Aggressive</option>
                    <option value="Value">Value</option>
                    <option value="Income">Income</option>
                  </select>
                ) : (
                  <span className="option-value">{profile.investmentStyle}</span>
                )}
              </div>

              <div className="option-group">
                <label>Risk Tolerance</label>
                {isEditing ? (
                  <select
                    name="riskTolerance"
                    value={editedProfile.riskTolerance}
                    onChange={handleChange}
                  >
                    <option value="Low">Low</option>
                    <option value="Moderate">Moderate</option>
                    <option value="High">High</option>
                  </select>
                ) : (
                  <span className="option-value">{profile.riskTolerance}</span>
                )}
              </div>

              <div className="option-group">
                <label>Investment Experience</label>
                {isEditing ? (
                  <select
                    name="experience"
                    value={editedProfile.experience}
                    onChange={handleChange}
                  >
                    <option value="Less than 1 year">Less than 1 year</option>
                    <option value="1-3 years">1-3 years</option>
                    <option value="3-5 years">3-5 years</option>
                    <option value="5-10 years">5-10 years</option>
                    <option value="10+ years">10+ years</option>
                  </select>
                ) : (
                  <span className="option-value">{profile.experience}</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Profile
