import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// StrictMode intentionally omitted — it double-invokes effects which breaks
// the Cesium Viewer singleton lifecycle.
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
