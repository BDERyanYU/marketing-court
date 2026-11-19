import React from 'react'
import ReactDOM from 'react-dom/client'

async function start() {
  const version = new URLSearchParams(window.location.search).get('ui')
  const [{ default: App }] =
    version === 'v1'
      ? await Promise.all([import('./v1/App'), import('./v1/style.css')])
      : version === 'v2'
        ? await Promise.all([import('./App'), import('./style.css')])
        : await Promise.all([import('./v3/App'), import('./v3/style.css')])

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
}

void start()
