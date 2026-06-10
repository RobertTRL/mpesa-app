import redcross from '../assets/redcross.webp'
import { useNavigate } from 'react-router-dom'

export default function Failure() {
  const navigate = useNavigate()

  return (
    <div className="payment-page">
      <div className="payment-inner">

        <div className="header">
          <h1>Payment Failed</h1>
          <p>Something went wrong with your payment. Please try again.</p>
        </div>

        <div className="form-card">
          <div className="form-card-bar" style={{ background: '#EF4444' }} />
          <div className="form-inner" style={{ alignItems: 'center', textAlign: 'center' }}>

            <img
              src={redcross}
              alt="Payment failed"
              style={{ width: '8rem', height: '8rem', objectFit: 'contain' }}
            />

            <p style={{ fontSize: '0.875rem', color: '#7C83A0', lineHeight: 1.6 }}>
              Your M-Pesa payment could not be completed. This may be due to
              insufficient funds, an incorrect PIN, or a cancelled request.
            </p>

            <button
              className="submit-btn"
              style={{ background: '#EF4444' }}
              onClick={() => navigate('/')}
            >
              Go back home
            </button>

          </div>
        </div>

      </div>
    </div>
  )
}