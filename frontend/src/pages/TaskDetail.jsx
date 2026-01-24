import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  Row, 
  Col, 
  Card, 
  Typography, 
  Tag, 
  Button, 
  Space, 
  Descriptions,
  Timeline,
  Spin,
  Empty,
} from 'antd'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  SearchOutlined,
  BulbOutlined,
  CodeOutlined,
  ExperimentOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import api from '../services/api'

const { Title, Text, Paragraph } = Typography

// Step type icons
const stepIcons = {
  RAG_QUERY: <SearchOutlined />,
  HYPOTHESIS: <BulbOutlined />,
  CODE_GEN: <CodeOutlined />,
  VALIDATE: <CheckCircleOutlined />,
  SIMULATE: <ExperimentOutlined />,
  SELF_CORRECT: <SyncOutlined />,
  EVALUATE: <CheckCircleOutlined />,
}

// Step status colors
const statusColors = {
  SUCCESS: 'green',
  FAILED: 'red',
  RUNNING: 'processing',
  SKIPPED: 'default',
}

export default function TaskDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  // Fetch task details with trace
  const { data: task, isLoading, error } = useQuery({
    queryKey: ['task', id],
    queryFn: () => api.getTask(id),
    refetchInterval: 5000, // Refresh while task is running
  })

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (error || !task) {
    return (
      <Empty description="任务未找到">
        <Button onClick={() => navigate('/tasks')}>返回任务列表</Button>
      </Empty>
    )
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircleOutlined style={{ color: '#00ff88' }} />
      case 'FAILED':
        return <CloseCircleOutlined style={{ color: '#ff4757' }} />
      case 'RUNNING':
        return <LoadingOutlined style={{ color: '#00d4ff' }} spin />
      default:
        return null
    }
  }

  return (
    <div>
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
              返回
            </Button>
            <Title level={3} style={{ margin: 0 }}>
              {task.task_name}
            </Title>
            <Tag color={statusColors[task.status] || 'default'}>{task.status}</Tag>
          </Space>
        </Col>
        <Col>
          <Space>
            {task.status === 'PENDING' && (
              <Button type="primary" icon={<PlayCircleOutlined />}>
                启动
              </Button>
            )}
            {task.status === 'RUNNING' && (
              <Button icon={<PauseCircleOutlined />}>
                暂停
              </Button>
            )}
            {['RUNNING', 'PAUSED'].includes(task.status) && (
              <Button danger icon={<StopOutlined />}>
                停止
              </Button>
            )}
          </Space>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Left: Task Info */}
        <Col xs={24} lg={8}>
          <Card className="glass-card" title="任务详情">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="地区">{task.region}</Descriptions.Item>
              <Descriptions.Item label="股票池">{task.universe}</Descriptions.Item>
              <Descriptions.Item label="策略">
                <Tag color={task.dataset_strategy === 'AUTO' ? 'cyan' : 'purple'}>
                  {task.dataset_strategy}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模式">
                {task.agent_mode}
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                <Text strong style={{ color: '#00d4ff' }}>
                  {task.progress_current} / {task.daily_goal}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="已发现 Alpha">
                {task.alphas_count || 0}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(task.created_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* Right: Trace Timeline */}
        <Col xs={24} lg={16}>
          <Card 
            className="glass-card" 
            title="挖掘轨迹 (RD-Agent 视角)"
            extra={<Text type="secondary">{task.trace_steps?.length || 0} 个步骤</Text>}
          >
            {task.trace_steps && task.trace_steps.length > 0 ? (
              <Timeline mode="left">
                {task.trace_steps.map((step, index) => (
                  <Timeline.Item
                    key={step.id}
                    dot={getStatusIcon(step.status)}
                    color={statusColors[step.status] || 'gray'}
                  >
                    <Card 
                      size="small" 
                      style={{ 
                        background: 'rgba(0,0,0,0.2)',
                        marginBottom: 8,
                      }}
                    >
                      <Space>
                        {stepIcons[step.step_type]}
                        <Text strong>Step {step.step_order}: {step.step_type}</Text>
                        <Tag>{step.duration_ms ? `${step.duration_ms}ms` : '--'}</Tag>
                      </Space>
                      
                      {/* Show input/output for some steps */}
                      {step.step_type === 'HYPOTHESIS' && step.output_data?.hypothesis && (
                        <Paragraph 
                          style={{ 
                            marginTop: 8, 
                            marginBottom: 0,
                            color: 'rgba(255,255,255,0.65)',
                          }}
                          ellipsis={{ rows: 2 }}
                        >
                          💡 {step.output_data.hypothesis}
                        </Paragraph>
                      )}
                      
                      {step.step_type === 'CODE_GEN' && step.output_data?.expression && (
                        <pre style={{ 
                          marginTop: 8, 
                          marginBottom: 0,
                          fontSize: 12,
                          maxHeight: 100,
                          overflow: 'auto',
                        }}>
                          {step.output_data.expression}
                        </pre>
                      )}
                      
                      {step.error_message && (
                        <Text type="danger" style={{ display: 'block', marginTop: 8 }}>
                          ❌ {step.error_message}
                        </Text>
                      )}
                    </Card>
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <Empty description="暂无轨迹记录" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
