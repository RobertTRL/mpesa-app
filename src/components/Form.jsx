import { useState, useId } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Form() {
  const numberId = useId()
  const amountId = useId()
  const [details, setDetails] = useState({ number: '', amount: '' })
  const [isNumberValid, setIsNumberValid] = useState(false)
  const [isAmountValid, setIsAmountValid] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const navigate = useNavigate()

  const handleChange = (e) => {
    setDetails((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const validateNumber = () => {
    setIsNumberValid(details.number.length === 10 && details.number[0] === '0')
  }

  const validateAmount = () => {
    setIsAmountValid(Number(details.amount) >= 1)
  }

  const pollStatus = async (checkoutId) => {
    const MAX_ATTEMPTS = 10
    const INTERVAL_MS = 3000

    for (let i = 0; i < MAX_ATTEMPTS; i++) {
      await new Promise(r => setTimeout(r, INTERVAL_MS))

      const res = await fetch(
        `https://mpesa-app-indol.vercel.app/api/status?id=${checkoutId}`
      )
      const data = await res.json()

      if (data.found) {
        if (Number(data.resultCode) === 0) {
          navigate('/success', {
            state: {
              receipt: data.receipt,
              amount: data.amount,
              phone: data.phone,
            },
          })
        } else {
          throw new Error(data.resultDesc)
        }
      }
    }

    throw new Error("Payment confirmation timed out. Check your M-Pesa messages.")
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await fetch("https://mpesa-app-indol.vercel.app/api/pay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone: String(details.number),
          amount: Number(details.amount),
        }),
      })

      const data = await res.json()
      if (!res.ok || !data.success) throw new Error(data.error || "Payment initiation failed")

      await pollStatus(data.CheckoutRequestID)

    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <div className="form-card-bar" />
      <div className="form-inner">
        <p className="form-heading">Payment details</p>

        <div className="field">
          <label htmlFor={numberId}>Mobile number</label>
          <input
            type="text"
            placeholder="0123 456 789"
            id={numberId}
            onChange={handleChange}
            onBlur={validateNumber}
            maxLength={10}
            value={details.number}
            name="number"
          />
          {!isNumberValid && !!details.number.length && (
            <p className="warning">Enter a valid number</p>
          )}
        </div>

        <div className="field">
          <label htmlFor={amountId}>Amount (KSH)</label>
          <input
            type="number"
            placeholder="100"
            id={amountId}
            onChange={handleChange}
            onBlur={validateAmount}
            value={details.amount}
            name="amount"
            min={1}
          />
          {!isAmountValid && !!details.amount.length && (
            <p className="warning">Enter a valid amount</p>
          )}
        </div>

        {error && <p className="warning">{error}</p>}

        <button
          type="submit"
          className="submit-btn"
          disabled={!isNumberValid || !isAmountValid || loading}
        >
          {loading ? <div className="loader"></div> : "Send payment"}
        </button>

      </div>
    </form>
  )
}