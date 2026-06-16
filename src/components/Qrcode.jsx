import { useState, useEffect } from 'react'

export default function Qrcode({ amount }) {
  const [qr, setQr]           = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  useEffect(() => {
    if (!amount || Number(amount) < 1) {
      setQr(null)
      return
    }

    let cancelled = false
    setQr(null)        // ← clear the old QR immediately when amount changes
    setError(null)

    const timer = setTimeout(() => {
      setLoading(true)

      fetch('https://mpesa-app-indol.vercel.app/api/qrcode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: Number(amount) }),
      })
        .then(r => r.json())
        .then(data => {
          if (cancelled) return
          if (data.success) setQr(data.qr)
          else setError(data.error)
        })
        .catch(e => { if (!cancelled) setError(e.message) })
        .finally(() => { if (!cancelled) setLoading(false) })
    }, 3000)

    return () => {
      clearTimeout(timer)
      cancelled = true
    }
  }, [amount])

  if (!amount || Number(amount) < 1) return null

  return (
    <div className="qr-card">
      <p className="qr-label">Or scan to pay</p>
      <div className="qr-box">
        {loading && <p className="timeout">Generating QR…</p>}
        {error   && <p className="warning">{error}</p>}
        {qr && (
          <img
            src={`data:image/png;base64,${qr}`}
            alt="M-Pesa QR code"
            width={180}
            height={180}
          />
        )}
      </div>
    </div>
  )
}