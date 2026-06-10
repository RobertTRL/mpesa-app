import { useState, useId } from 'react'
 
export default function Form() {
  const numberId = useId()
  const amountId = useId()
  const [details, setDetails] = useState({ number: '', amount: '' })
 
  const handleChange = (e) => {
    setDetails((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }
 
  return (
    <div className="form-card">
      <div className="form-card-bar" />
      <div className="form-inner">
        <p className="form-heading">Payment details</p>
 
        <div className="field">
          <label htmlFor={numberId}>Mobile number</label>
          <input
            type="text"
            placeholder="0XXX XXX XXX"
            id={numberId}
            onChange={handleChange}
            value={details.number}
            name="number"
          />
        </div>
 
        <div className="field">
          <label htmlFor={amountId}>Amount (KES)</label>
          <input
            type="number"
            placeholder="0.00"
            id={amountId}
            onChange={handleChange}
            value={details.amount}
            name="amount"
          />
        </div>
 
        <button type="submit" className="submit-btn">
          Send prompt
        </button>
      </div>
    </div>
  )
}