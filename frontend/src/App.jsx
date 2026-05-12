import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import AppSidebar from './components/AppSidebar'
import AppHeader from './components/AppHeader'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './pages/Dashboard'
import TaskManagement from './pages/TaskManagement'
import TaskDetail from './pages/TaskDetail'
import AlphaLab from './pages/AlphaLab'
import AlphaDetail from './pages/AlphaDetail'
import ConfigCenter from './pages/ConfigCenter'
import DataManagement from './pages/DataManagement'

const { Content } = Layout

function App() {
  return (
    <ErrorBoundary>
      <Layout style={{ minHeight: '100vh' }}>
        <AppSidebar />
        <Layout>
          <AppHeader />
          <Content style={{ padding: '24px', overflow: 'auto' }}>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
              <Route path="/tasks" element={<ErrorBoundary><TaskManagement /></ErrorBoundary>} />
              <Route path="/tasks/:id" element={<ErrorBoundary><TaskDetail /></ErrorBoundary>} />
              <Route path="/alphas" element={<ErrorBoundary><AlphaLab /></ErrorBoundary>} />
              <Route path="/alphas/:id" element={<ErrorBoundary><AlphaDetail /></ErrorBoundary>} />
              <Route path="/data" element={<ErrorBoundary><DataManagement /></ErrorBoundary>} />
              <Route path="/config" element={<ErrorBoundary><ConfigCenter /></ErrorBoundary>} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </ErrorBoundary>
  )
}

export default App
