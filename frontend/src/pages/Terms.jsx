import { Link } from 'react-router-dom'

const Terms = () => (
  <div style={{ maxWidth: 800, margin: '60px auto', padding: '0 24px', color: '#e2e8f0', lineHeight: 1.8 }}>
    <h1 style={{ marginBottom: 8 }}>Terms &amp; Conditions</h1>
    <p style={{ color: '#a0aec0', marginBottom: 32 }}>Last updated: March 2026</p>

    <h2>1. Acceptance of Terms</h2>
    <p>By accessing and using MarketMind AI, you agree to be bound by these Terms and Conditions. If you do not agree, please do not use this platform.</p>

    <h2>2. Use of the Platform</h2>
    <p>MarketMind AI is intended for informational and educational purposes only. The content provided, including stock data, AI analysis, and chatbot responses, does not constitute financial advice. Always consult a qualified financial advisor before making investment decisions.</p>

    <h2>3. User Accounts</h2>
    <p>You are responsible for maintaining the confidentiality of your account credentials. You agree to notify us immediately of any unauthorised use of your account.</p>

    <h2>4. Data &amp; Privacy</h2>
    <p>We collect only the data necessary to provide the service. Your personal information is never sold to third parties.</p>

    <h2>5. Disclaimer of Warranties</h2>
    <p>The platform is provided &quot;as is&quot; without warranties of any kind. Market data may be delayed. We do not guarantee the accuracy, completeness, or timeliness of any information.</p>

    <h2>6. Limitation of Liability</h2>
    <p>MarketMind AI shall not be liable for any financial losses or damages arising from reliance on the information provided on this platform.</p>

    <h2>7. Changes to Terms</h2>
    <p>We reserve the right to update these terms at any time. Continued use of the platform after changes constitutes acceptance of the new terms.</p>

    <div style={{ marginTop: 40 }}>
      <Link to="/register" style={{ color: '#00d4ff' }}>&larr; Back to Register</Link>
    </div>
  </div>
)

export default Terms
