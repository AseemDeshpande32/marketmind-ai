import { useState } from 'react'
import { FiUser, FiMail, FiPhone, FiMapPin, FiEdit2, FiSave, FiCamera } from 'react-icons/fi'
import './Profile.css'

const Profile = () => {
  const [isEditing, setIsEditing] = useState(false)
  const [profile, setProfile] = useState({
    fullName: 'John Doe',
    email: 'john.doe@example.com',
    phone: '+1 (555) 123-4567',
    location: 'New York, USA',
    bio: 'Passionate investor with a focus on technology and growth stocks. Building wealth through smart, data-driven investment decisions.',
    investmentStyle: 'Growth',
    riskTolerance: 'Moderate',
    experience: '3-5 years'
  })

  const [editedProfile, setEditedProfile] = useState(profile)

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

  return (
    <div className="profile-page">
      <div className="profile-header">
        <h1>My Profile</h1>
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

      <div className="profile-content">
        <div className="profile-card main-info">
          <div className="avatar-section">
            <div className="avatar">
              <span>{profile.fullName.split(' ').map(n => n[0]).join('')}</span>
              {isEditing && (
                <button className="avatar-edit">
                  <FiCamera />
                </button>
              )}
            </div>
            <div className="user-name">
              <h2>{profile.fullName}</h2>
              <span className="member-since">Member since Jan 2024</span>
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

        <div className="profile-card stats-card">
          <h3>Activity Summary</h3>
          <div className="stats-grid">
            <div className="stat-box">
              <span className="stat-number">47</span>
              <span className="stat-label">Stocks Analyzed</span>
            </div>
            <div className="stat-box">
              <span className="stat-number">128</span>
              <span className="stat-label">Chat Sessions</span>
            </div>
            <div className="stat-box">
              <span className="stat-number">12</span>
              <span className="stat-label">Watchlist Items</span>
            </div>
            <div className="stat-box">
              <span className="stat-number">89%</span>
              <span className="stat-label">Profile Complete</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Profile
