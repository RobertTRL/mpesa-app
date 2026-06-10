import { useState, useId } from 'react'

export default function Form() {
  const numberId = useId()
  const amountId = useId()
  const [details, setDetails] = useState({ number: '', amount: '' })
  const [isNumberValid, setIsNumberValid] = useState(false)
  const [isAmountValid, setIsAmountValid] = useState(false)

  const handleChange = (e) => {
    setDetails((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const validateNumber = () => {
    setIsNumberValid(details.number.length === 10 && details.number[0] === '0')
  }

  const validateAmount = () => {
    setIsAmountValid(Number(details.amount) >= 1)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log(details)
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

        <button
          type="submit"
          className="submit-btn"
          disabled={!isNumberValid || !isAmountValid}
        >
          Send payment
        </button>
      </div>
    </form>
  )
}