import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Row, 
  Col, 
  Card, 
  Table, 
  Button, 
  Tag, 
  Space, 
  Typography,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
} from 'antd'
import {
  PlusOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import api from '../services/api'

const { Title } = Typography
const { Option } = Select

export default function TaskManagement() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Fetch tasks
  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => api.getTasks({ limit: 50 }),
    refetchInterval: 10000,
  })

  // Create task mutation
  const createTaskMutation = useMutation({
    mutationFn: api.createTask,
    onSuccess: () => {
      message.success('任务创建成功')
      queryClient.invalidateQueries(['tasks'])
      setIsModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('任务创建失败')
    },
  })

  // Start task mutation
  const startTaskMutation = useMutation({
    mutationFn: api.startTask,
    onSuccess: () => {
      message.success('任务已启动')
      queryClient.invalidateQueries(['tasks'])
    },
  })

  const handleCreateTask = (values) => {
    createTaskMutation.mutate(values)
  }

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      render: (text, record) => (
        <a onClick={() => navigate(`/tasks/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '地区',
      dataIndex: 'region',
      key: 'region',
      width: 100,
    },
    {
      title: '股票池',
      dataIndex: 'universe',
      key: 'universe',
      width: 120,
    },
    {
      title: '模式',
      dataIndex: 'agent_mode',
      key: 'agent_mode',
      width: 120,
      render: (mode) => (
        <Tag color={mode === 'AUTONOMOUS' ? 'blue' : 'purple'}>
          {mode}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const colors = {
          PENDING: 'default',
          RUNNING: 'processing',
          PAUSED: 'warning',
          COMPLETED: 'success',
          FAILED: 'error',
          STOPPED: 'default',
        }
        return <Tag color={colors[status] || 'default'}>{status}</Tag>
      },
    },
    {
      title: '进度',
      key: 'progress',
      width: 100,
      render: (_, record) => (
        <span>{record.progress_current} / {record.daily_goal}</span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          {record.status === 'PENDING' && (
            <Button 
              size="small" 
              type="primary" 
              icon={<PlayCircleOutlined />}
              onClick={() => startTaskMutation.mutate(record.id)}
            >
              启动
            </Button>
          )}
          {record.status === 'RUNNING' && (
            <Button 
              size="small" 
              icon={<PauseCircleOutlined />}
              onClick={() => api.interveneTask(record.id, 'PAUSE')}
            >
              暂停
            </Button>
          )}
          <Button 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => navigate(`/tasks/${record.id}`)}
          >
            查看
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ThunderboltOutlined style={{ marginRight: 12, color: '#00d4ff' }} />
            任务管理
          </Title>
        </Col>
        <Col>
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => setIsModalOpen(true)}
          >
            创建任务
          </Button>
        </Col>
      </Row>

      <Card className="glass-card">
        <Table
          columns={columns}
          dataSource={tasks || []}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create Task Modal */}
      <Modal
        title="创建挖掘任务"
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateTask}
          initialValues={{
            region: 'USA',
            universe: 'TOP3000',
            dataset_strategy: 'AUTO',
            agent_mode: 'AUTONOMOUS',
            daily_goal: 4,
          }}
        >
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如: 美股动量因子挖掘" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="region" label="地区">
                <Select>
                  <Option value="USA">USA</Option>
                  <Option value="CHN">中国 (China)</Option>
                  <Option value="ASI">亚洲 (Asia)</Option>
                  <Option value="EUR">欧洲 (Europe)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="universe" label="股票池">
                <Select>
                  <Option value="TOP3000">TOP3000</Option>
                  <Option value="TOP500">TOP500</Option>
                  <Option value="TOP1000">TOP1000</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="dataset_strategy" label="数据集策略">
                <Select>
                  <Option value="AUTO">自动探索 (Hierarchical RAG)</Option>
                  <Option value="SPECIFIC">指定数据集</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="agent_mode" label="Agent 模式">
                <Select>
                  <Option value="AUTONOMOUS">自动 (Fully Auto)</Option>
                  <Option value="INTERACTIVE">交互 (Step-by-step)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="daily_goal" label="每日目标 (Alpha 数量)">
            <InputNumber min={1} max={20} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setIsModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={createTaskMutation.isLoading}>
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
