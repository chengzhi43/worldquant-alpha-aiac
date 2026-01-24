import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Row, 
  Col, 
  Card, 
  Typography, 
  Tabs,
  Slider,
  Switch,
  Table,
  Tag,
  Button,
  Space,
  InputNumber,
  Form,
  message,
} from 'antd'
import {
  SettingOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import api from '../services/api'

const { Title, Text } = Typography

export default function ConfigCenter() {
  const queryClient = useQueryClient()

  // Fetch knowledge entries
  const { data: successPatterns, isLoading: patternsLoading } = useQuery({
    queryKey: ['knowledge', 'success-patterns'],
    queryFn: () => api.getSuccessPatterns(30),
  })

  const { data: failurePitfalls, isLoading: pitfallsLoading } = useQuery({
    queryKey: ['knowledge', 'failure-pitfalls'],
    queryFn: () => api.getFailurePitfalls(30),
  })

  const knowledgeColumns = [
    {
      title: '模式',
      dataIndex: 'pattern',
      key: 'pattern',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active) => (
        <Tag color={active ? 'success' : 'default'}>
          {active ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
    {
      title: '来源',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 80,
      render: (source) => (
        <Tag color={source === 'USER' ? 'blue' : 'default'}>{source}</Tag>
      ),
    },
  ]

  const tabs = [
    {
      key: 'thresholds',
      label: '质量阈值',
      children: (
        <Card className="glass-card">
          <Form layout="vertical" style={{ maxWidth: 500 }}>
            <Form.Item label="最低夏普比率 (Sharpe Ratio)">
              <Row gutter={16}>
                <Col span={16}>
                  <Slider 
                    min={0} 
                    max={5} 
                    step={0.1} 
                    defaultValue={1.5}
                    marks={{ 0: '0', 1: '1', 1.5: '1.5', 2: '2', 3: '3', 5: '5' }}
                  />
                </Col>
                <Col span={8}>
                  <InputNumber min={0} max={5} step={0.1} defaultValue={1.5} style={{ width: '100%' }} />
                </Col>
              </Row>
            </Form.Item>

            <Form.Item label="最高换手率 (Turnover)">
              <Row gutter={16}>
                <Col span={16}>
                  <Slider 
                    min={0} 
                    max={2} 
                    step={0.1} 
                    defaultValue={0.7}
                    marks={{ 0: '0', 0.5: '0.5', 1: '1', 1.5: '1.5', 2: '2' }}
                  />
                </Col>
                <Col span={8}>
                  <InputNumber min={0} max={2} step={0.1} defaultValue={0.7} style={{ width: '100%' }} />
                </Col>
              </Row>
            </Form.Item>

            <Form.Item label="最低适应度 (Fitness)">
              <Row gutter={16}>
                <Col span={16}>
                  <Slider 
                    min={0} 
                    max={1} 
                    step={0.05} 
                    defaultValue={0.6}
                    marks={{ 0: '0', 0.5: '0.5', 1: '1' }}
                  />
                </Col>
                <Col span={8}>
                  <InputNumber min={0} max={1} step={0.05} defaultValue={0.6} style={{ width: '100%' }} />
                </Col>
              </Row>
            </Form.Item>

            <Form.Item label="最大相关性 (多样性)">
              <Row gutter={16}>
                <Col span={16}>
                  <Slider 
                    min={0} 
                    max={1} 
                    step={0.05} 
                    defaultValue={0.7}
                    marks={{ 0: '0', 0.5: '0.5', 0.7: '0.7', 1: '1' }}
                  />
                </Col>
                <Col span={8}>
                  <InputNumber min={0} max={1} step={0.05} defaultValue={0.7} style={{ width: '100%' }} />
                </Col>
              </Row>
            </Form.Item>

            <Form.Item>
              <Button type="primary" icon={<SaveOutlined />}>
                保存设置
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'operators',
      label: '算子偏好',
      children: (
        <Card className="glass-card">
          <Table
            dataSource={[
              { operator: 'ts_rank', usage: 234, success_rate: 78, status: 'ACTIVE' },
              { operator: 'ts_corr', usage: 189, success_rate: 82, status: 'ACTIVE' },
              { operator: 'ts_zscore', usage: 156, success_rate: 75, status: 'ACTIVE' },
              { operator: 'grouped_rank', usage: 98, success_rate: 71, status: 'ACTIVE' },
              { operator: 'ts_product', usage: 45, success_rate: 12, status: 'BANNED' },
            ]}
            columns={[
              { title: '算子', dataIndex: 'operator', key: 'operator' },
              { title: '使用次数', dataIndex: 'usage', key: 'usage' },
              { 
                title: '成功率', 
                dataIndex: 'success_rate', 
                key: 'success_rate',
                render: (rate) => (
                  <Text style={{ color: rate > 50 ? '#00ff88' : '#ff4757' }}>
                    {rate}%
                  </Text>
                ),
              },
              { 
                title: '状态', 
                dataIndex: 'status', 
                key: 'status',
                render: (status) => (
                  <Tag color={status === 'ACTIVE' ? 'success' : 'error'}>{status}</Tag>
                ),
              },
              {
                title: '操作',
                key: 'action',
                render: (_, record) => (
                  <Switch 
                    checked={record.status === 'ACTIVE'} 
                    checkedChildren="启用"
                    unCheckedChildren="禁用"
                  />
                ),
              },
            ]}
            rowKey="operator"
            pagination={false}
          />
        </Card>
      ),
    },
    {
      key: 'success-patterns',
      label: '成功模式',
      children: (
        <Card className="glass-card">
          <Table
            columns={knowledgeColumns}
            dataSource={successPatterns || []}
            rowKey="id"
            loading={patternsLoading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
    {
      key: 'failure-pitfalls',
      label: '失败教训',
      children: (
        <Card className="glass-card">
          <Table
            columns={knowledgeColumns}
            dataSource={failurePitfalls || []}
            rowKey="id"
            loading={pitfallsLoading}
            pagination={{ pageSize: 10 }}
          />
        </Card>
      ),
    },
  ]

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SettingOutlined style={{ marginRight: 12, color: '#00d4ff' }} />
        配置中心
      </Title>

      <Tabs items={tabs} size="large" />
    </div>
  )
}
