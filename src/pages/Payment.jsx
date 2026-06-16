import Form from "../components/Form.jsx"
import Header from "../components/Header.jsx"
import Qrcode from "../components/Qrcode.jsx"
import { useState } from "react"
import '../styles/payment.css'

export default function Payment(){
    const [details, setDetails] = useState({ number: '', amount: '' })
    return (
        <div className="payment-page">
            <div className="payment-inner">
                <Header />
                <Form details={details} setDetails={setDetails}/>
                <Qrcode amount={details.amount}/>
            </div>
        </div>
    )
}