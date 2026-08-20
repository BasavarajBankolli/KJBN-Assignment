import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

function App() {
  return <div className="app">Food Truck Finder</div>
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
