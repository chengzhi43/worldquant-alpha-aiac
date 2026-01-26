import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider, theme } from 'antd'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
})

// Dark theme configuration for "Future FinTech" aesthetic
const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#00d4ff', // Cyan accent
    colorBgContainer: '#131a2b',
    colorBgLayout: '#0a0e17',
    borderRadius: 8,
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
  },
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={darkTheme}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
