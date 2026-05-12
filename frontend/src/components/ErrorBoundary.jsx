import { Component } from 'react'
import { Button, Result } from 'antd'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught:', error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  handleRefresh = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      const isDev = import.meta.env.DEV

      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <Result
          status="error"
          title="页面渲染异常"
          subTitle={isDev ? this.state.error?.message : '发生了一个意外错误，请刷新页面重试'}
          extra={[
            <Button key="refresh" type="primary" onClick={this.handleRefresh}>
              刷新页面
            </Button>,
            <Button key="reset" onClick={this.handleReset}>
              重试
            </Button>,
          ]}
        >
          {isDev && this.state.error && (
            <div style={{ marginTop: 16, padding: 12, background: '#1f1f1f', borderRadius: 4, fontSize: 12, maxHeight: 300, overflow: 'auto' }}>
              <pre style={{ margin: 0, color: '#ff4757' }}>{this.state.error.toString()}</pre>
              <pre style={{ margin: 0, color: '#888', marginTop: 8 }}>{this.state.errorInfo?.componentStack}</pre>
            </div>
          )}
        </Result>
      )
    }

    return this.props.children
  }
}
