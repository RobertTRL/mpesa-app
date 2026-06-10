import { Routes, Route } from "react-router-dom";
import Payment from "./Payment.jsx";
// import Success from "./Success.jsx";
// import Failure from "./Failure.jsx";
// import Loading from "./Loading.jsx";
import '../styles/app.css'

export default function App(){
    return (
        <Routes>
            <Route index element={<Payment />}/>
            {/* <Route path="/success" element={<Success />}/>
            <Route path="/failure" element={<Failure />}/>
            <Route path="/loading" element={<Loading />}/> */}
        </Routes>
    )
}