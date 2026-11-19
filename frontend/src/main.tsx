import React from 'react'
import ReactDOM from 'react-dom/client'

async function start() {
  const firstVersion = new URLSearchParams(window.location.search).get('ui') === 'v1'
  const [{ default: App }] = firstVersion
    ? await Promise.all([import('./v1/App'), import('./v1/style.css')])
    : await Promise.all([import('./App'), import('./style.css')])

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
}

void start()
