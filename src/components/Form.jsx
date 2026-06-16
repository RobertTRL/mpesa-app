import { useState, useId } from 'react'
import { useNavigate } from 'react-router-dom'
import { waitForPayment } from '../../utils/waitForPayment'

export default function Form({ details, setDetails }) {
  const numberId = useId()
  const amountId = useId()
  const [isNumberValid, setIsNumberValid] = useState(false)
  const [isAmountValid, setIsAmountValid] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const navigate = useNavigate()

  const handleChange = (e) => {
    const { name, value } = e.target
    setDetails((prev) => ({ ...prev, [name]: value }))
    if (name === 'number') {
      setIsNumberValid(value.length === 10 && value[0] === '0')
    }
    if (name === 'amount') {
      setIsAmountValid(Number(value) >= 1)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // 1. Trigger STK Push
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

      // 2. Wait for callback → Supabase → instant notification

      const payment = await waitForPayment(data.checkout_request_id)

      // 3. Redirect based on result

      if (payment.result_code === 0) {
        navigate('/success', {
          state: {
            receipt: payment.mpesa_receipt,
            amount: payment.amount,
            phone: payment.phone,
          },
        })

      } else {

        navigate('/failure', {
          state: { reason: payment.result_desc },
        })
      }

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
            value={details.amount}
            name="amount"
            min={1}
          />
          {!isAmountValid && !!details.amount.length && (
            <p className="warning">Enter a valid amount</p>
          )}
        </div>
        {error && <p className="warning">{error}</p>}
        {loading && (
          <p className="timeout">Check your phone and enter your M-Pesa PIN…</p>
        )}
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