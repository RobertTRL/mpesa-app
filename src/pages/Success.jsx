import { useNavigate, useLocation } from 'react-router-dom'
import greencheck from '../assets/greencheck.png'

export default function Success() {
  const navigate = useNavigate()
  const { state } = useLocation()

  return (
    <div className="payment-page">
      <div className="payment-inner">

        <div className="header">
          <h1>Payment Successful</h1>
          <p>Your M-Pesa payment was completed successfully.</p>
        </div>

        <div className="form-card">
          <div className="form-card-bar" style={{ background: '#10B981' }} />
          <div className="form-inner" style={{ alignItems: 'center', textAlign: 'center' }}>

            <img
              src={greencheck}
              alt="Payment successful"
              style={{ width: '8rem', height: '8rem', objectFit: 'contain' }}
            />

            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div className="field">
                <label>Receipt number</label>
                <p style={{ fontWeight: 600, color: '#1E1B4B', paddingBlock: '0.65em' }}>
                  {state?.receipt ?? '—'}
                </p>
              </div>
              <div className="field">
                <label>Amount</label>
                <p style={{ fontWeight: 600, color: '#1E1B4B', paddingBlock: '0.65em' }}>
                  KSH {state?.amount ?? '—'}
                </p>
              </div>
              <div className="field">
                <label>Phone</label>
                <p style={{ fontWeight: 600, color: '#1E1B4B', paddingBlock: '0.65em' }}>
                  {state?.phone ?? '—'}
                </p>
              </div>
            </div>

            <button
              className="submit-btn"
              style={{ background: '#10B981' }}
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