import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import type { Plugin } from 'vite'

const entry = (path: string) =>
  decodeURIComponent(new URL(path, import.meta.url).pathname).replace(/^\/(?=[A-Za-z]:\/)/, '')

// Keep the welcome page separate from the existing React workspace.
function workspaceRoutes(): Plugin {
  const install = (server: {
    middlewares: {
      use: (handler: (req: { url?: string }, res: unknown, next: () => void) => void) => void
    }
  }) => {
    server.middlewares.use((req, _res, next) => {
      const url = new URL(req.url ?? '/', 'http://localhost')
      const route = url.pathname.replace(/\/$/, '')
      if (route === '/review' || route === '/jury') req.url = `${route}/index.html${url.search}`
      else if (
        url.pathname === '/' &&
        ['v1', 'v2', 'v3'].includes(url.searchParams.get('ui') ?? '')
      )
        req.url = `/review/index.html${url.search}`
      next()
    })
  }
  return { name: 'workspace-routes', configureServer: install, configurePreviewServer: install }
}

export default defineConfig(({ mode }) => {
  const backend = loadEnv(mode, '.', 'VITE_').VITE_BACKEND_URL || 'http://127.0.0.1:8000'
  return {
    plugins: [workspaceRoutes(), react()],
    build: {
      rollupOptions: {
        input: {
          welcome: entry('./index.html'),
          review: entry('./review/index.html'),
          jury: entry('./jury/index.html'),
        },
      },
    },
    server: {
      proxy: {
        '/api': backend,
        '/health': backend,
      },
    },
  }
})
