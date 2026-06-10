import Form from "../components/Form.jsx"
import Header from "../components/Header.jsx"
import Qrcode from "../components/Qrcode.jsx"
import '../styles/payment.css'

export default function Payment(){
    return (
        <div className="payment-page">
            <div className="payment-inner">
                <Header />
                <Form />
                <Qrcode />
            </div>
        </div>
    )
}