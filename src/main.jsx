import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Analytics } from "@vercel/analytics/react"
import './styles/index.css'
import App from './pages/App.jsx'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <div className="app-container">
        <App />
      </div>
      <Analytics/>
    </BrowserRouter>
  </StrictMode>,
)
