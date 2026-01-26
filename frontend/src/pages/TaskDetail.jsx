import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  Collapse,
  Spin,
  Empty,
  message,
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
  ReloadOutlined,
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

  const queryClient = useQueryClient()

  // Start task mutation
  const startTaskMutation = useMutation({
    mutationFn: api.startTask,
    onSuccess: () => {
      message.success('任务已启动')
      queryClient.invalidateQueries(['task', id])
    },
    onError: (err) => {
        message.error(`启动失败: ${err.message}`)
    }
  })

  // Intervene task mutation
  const interveneMutation = useMutation({
    mutationFn: ({ id, action }) => api.interveneTask(id, action),
    onSuccess: (_, variables) => {
      const actionMap = { PAUSE: '暂停', RESUME: '恢复', STOP: '停止' }
      message.success(`任务已${actionMap[variables.action]}`)
      queryClient.invalidateQueries(['task', id])
    },
  })

  const { Panel } = Collapse
  
  // Sort and group steps by iteration
  const groupedSteps = React.useMemo(() => {
    if (!task?.trace_steps) return {}
    
    // Sort steps by ID/order first
    const sortedSteps = [...task.trace_steps].sort((a, b) => a.step_order - b.step_order)
    
    const groups = {}
    sortedSteps.forEach(step => {
      const iter = step.iteration || 1 // Default to 1 if missing
      if (!groups[iter]) {
        groups[iter] = []
      }
      groups[iter].push(step)
    })
    return groups
  }, [task?.trace_steps])

  // Get iteration numbers sorted descending (latest first)
  const iterations = Object.keys(groupedSteps).map(Number).sort((a, b) => b - a)
  
  // Active keys for collapse (default to latest iteration)
  const [activeIterations, setActiveIterations] = React.useState([])

  React.useEffect(() => {
    if (iterations.length > 0 && activeIterations.length === 0) {
      setActiveIterations([iterations[0].toString()])
    }
  }, [iterations])

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
              <Button 
                type="primary" 
                icon={<PlayCircleOutlined />}
                loading={startTaskMutation.isLoading}
                onClick={() => startTaskMutation.mutate(task.id)}
              >
                启动
              </Button>
            )}
            {task.status === 'RUNNING' && (
              <Button 
                icon={<PauseCircleOutlined />}
                loading={interveneMutation.isLoading}
                onClick={() => interveneMutation.mutate({ id: task.id, action: 'PAUSE' })}
              >
                暂停
              </Button>
            )}
            {task.status === 'PAUSED' && (
              <Button 
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={interveneMutation.isLoading}
                onClick={() => interveneMutation.mutate({ id: task.id, action: 'RESUME' })}
              >
                恢复
              </Button>
            )}
            {['RUNNING', 'PAUSED'].includes(task.status) && (
              <Button 
                danger 
                icon={<StopOutlined />}
                loading={interveneMutation.isLoading}
                onClick={() => interveneMutation.mutate({ id: task.id, action: 'STOP' })}
              >
                停止
              </Button>
            )}
            {['FAILED', 'COMPLETED', 'STOPPED'].includes(task.status) && (
              <Button 
                type="primary" 
                icon={<ReloadOutlined />} 
                loading={startTaskMutation.isLoading}
                onClick={() => startTaskMutation.mutate(task.id)}
              >
                {task.status === 'COMPLETED' ? '重新运行' : '重试'}
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
              <Descriptions.Item label="最大迭代">
                {task.max_iterations || 1}
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
            title="挖掘轨迹 (进化循环)"
            extra={<Text type="secondary">共 {task.trace_steps?.length || 0} 步 / {iterations.length} 轮</Text>}
          >
            {task.trace_steps && task.trace_steps.length > 0 ? (
              <Collapse 
                bordered={false} 
                activeKey={activeIterations} 
                onChange={setActiveIterations}
                className="site-collapse-custom-collapse"
                style={{ background: 'transparent' }}
              >
                {iterations.map(iter => {
                   const steps = groupedSteps[iter]
                   // Try to find summary step for this iteration
                   const summaryStep = steps.find(s => s.step_type === 'ROUND_SUMMARY')
                   
                   const header = (
                     <Space>
                       <Text strong>第 {iter} 轮</Text>
                       {summaryStep && summaryStep.output_data?.success_rate !== undefined && (
                         <Tag color={summaryStep.output_data.success_rate > 0 ? 'green' : 'orange'}>
                           成功率: {(summaryStep.output_data.success_rate * 100).toFixed(0)}%
                         </Tag>
                       )}
                       <Text type="secondary" style={{ fontSize: 12 }}>({steps.length} 步)</Text>
                     </Space>
                   )

                   return (
                     <Panel header={header} key={iter.toString()} style={{ marginBottom: 12, border: '1px solid #303030', borderRadius: 8 }}>
                       <Timeline mode="left" style={{ marginTop: 16 }}>
                         {steps.map((step) => (
                           <Timeline.Item
                             key={step.id}
                             dot={getStatusIcon(step.status)}
                             color={statusColors[step.status] || 'gray'}
                           >
                             <Card 
                               size="small" 
                               style={{ 
                                 background: step.step_type === 'ROUND_SUMMARY' ? 'rgba(0, 50, 20, 0.2)' : 'rgba(0,0,0,0.2)',
                                 marginBottom: 8,
                                 borderColor: step.step_type === 'ROUND_SUMMARY' ? '#004d26' : undefined
                               }}
                             >
                               <Space>
                                 {stepIcons[step.step_type]}
                                 <Text strong>
                                    {step.step_type === 'ROUND_SUMMARY' ? '本轮总结' : `Step ${step.step_order}: ${step.step_type}`}
                                 </Text>
                                 <Tag>{step.duration_ms ? `${step.duration_ms}ms` : '--'}</Tag>
                               </Space>
                               
                               {/* Rich Content Rendering */}
                               
                               {/* RAG_QUERY: Show top patterns and pitfalls */}
                               {step.step_type === 'RAG_QUERY' && (
                                 <div style={{ marginTop: 8 }}>
                                   {step.output_data?.top_patterns?.length > 0 ? (
                                     <>
                                       <Text type="secondary" style={{ fontSize: 12 }}>参考模式:</Text>
                                       <ul style={{ paddingLeft: 20, margin: '4px 0', fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
                                         {step.output_data.top_patterns.map((p, i) => (
                                           <li key={i}>{p}</li>
                                         ))}
                                       </ul>
                                     </>
                                   ) : (
                                      <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>暂无参考模式</Text>
                                   )}
                                   
                                   {step.output_data?.top_pitfalls?.length > 0 && (
                                     <>
                                       <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>避坑指南:</Text>
                                       <ul style={{ paddingLeft: 20, margin: '4px 0', fontSize: 12, color: '#ff7875' }}>
                                         {step.output_data.top_pitfalls.map((p, i) => (
                                           <li key={i}>{p}</li>
                                         ))}
                                       </ul>
                                     </>
                                   )}
                                 </div>
                               )}
         
                               {/* DISTILL_CONTEXT: Show reasoning and selected concepts */}
                               {step.step_type === 'DISTILL_CONTEXT' && (
                                 <div style={{ marginTop: 8 }}>
                                   {step.output_data?.reasoning && (
                                     <Paragraph 
                                       ellipsis={{ rows: 2, expandable: true, symbol: '展开' }} 
                                       style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)', fontStyle: 'italic', marginBottom: 8 }}
                                     >
                                        "{step.output_data.reasoning}"
                                     </Paragraph>
                                   )}
                                   {step.output_data?.selected_concepts && (
                                     <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                       {step.output_data.selected_concepts.map((c, i) => (
                                         <Tag key={i} color="blue" style={{ fontSize: 11 }}>{c}</Tag>
                                       ))}
                                     </div>
                                   )}
                                 </div>
                               )}
         
                               {/* HYPOTHESIS: Show generated hypotheses */}
                               {step.step_type === 'HYPOTHESIS' && (
                                 <div style={{ marginTop: 8 }}>
                                    {step.output_data?.hypotheses?.map((h, i) => {
                                      const content = typeof h === 'string' ? h : (h.idea || JSON.stringify(h));
                                      const rationale = typeof h === 'object' && h.rationale ? h.rationale : null;
                                      
                                      return (
                                        <div key={i} style={{ marginBottom: 4 }}>
                                          <Paragraph ellipsis={{ rows: 2, expandable: true, symbol: '展开' }} style={{ fontSize: 13, marginBottom: 0 }}>
                                            <Text strong style={{ color: '#00d4ff', marginRight: 8 }}>H{i+1}:</Text>
                                            {content}
                                          </Paragraph>
                                          {rationale && (
                                            <Text type="secondary" style={{ fontSize: 12, marginLeft: 22 }}>
                                              {rationale}
                                            </Text>
                                          )}
                                        </div>
                                      );
                                    })}
                                    {/* Legacy support */}
                                    {!step.output_data?.hypotheses && step.output_data?.hypothesis && (
                                       <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 13 }}>
                                         💡 {step.output_data.hypothesis}
                                       </Paragraph>
                                    )}
                                 </div>
                               )}
                               
                               {/* CODE_GEN: Show expressions */}
                               {step.step_type === 'CODE_GEN' && step.output_data?.expressions && (
                                 <div style={{ marginTop: 8 }}>
                                    {step.output_data.expressions.map((expr, i) => (
                                      <pre key={i} style={{ 
                                        fontSize: 11, 
                                        background: '#1f1f1f', 
                                        padding: 4, 
                                        borderRadius: 4,
                                        marginBottom: 4,
                                        overflowX: 'auto'
                                      }}>
                                        {expr}
                                      </pre>
                                    ))}
                                 </div>
                               )}
                               
                               {/* SIMULATE: Show Results with Metrics */}
                               {step.step_type === 'SIMULATE' && step.output_data?.results && (
                                 <div style={{ marginTop: 8 }}>
                                   <Text type="secondary" style={{ fontSize: 12 }}>
                                     模拟结果: {step.output_data.success_count || 0} 成功
                                   </Text>
                                   {step.output_data.results.map((r, i) => (
                                     <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                                       <Tag color={r.err ? 'red' : 'blue'} style={{ fontSize: 11 }}>
                                         {r.id || `#${i+1}`}
                                       </Tag>
                                       {r.metrics && (
                                         <Space size="small" wrap>
                                           <Tag color={r.metrics.sharpe >= 1.2 ? 'green' : (r.metrics.sharpe >= 0 ? 'orange' : 'red')}>
                                             Sharpe: {r.metrics.sharpe?.toFixed(2) ?? '--'}
                                           </Tag>
                                           <Tag>Returns: {(r.metrics.returns * 100)?.toFixed(1) ?? '--'}%</Tag>
                                           <Tag>Turnover: {r.metrics.turnover?.toFixed(2) ?? '--'}</Tag>
                                           <Tag>Fitness: {r.metrics.fitness?.toFixed(2) ?? '--'}</Tag>
                                         </Space>
                                       )}
                                       {r.err && <Text type="danger" style={{ fontSize: 11 }}>{r.err}</Text>}
                                     </div>
                                   ))}
                                 </div>
                               )}
         
                               {/* EVALUATE: Show Pass/Fail Details */}
                               {step.step_type === 'EVALUATE' && step.output_data?.details && (
                                 <div style={{ marginTop: 8 }}>
                                   <Text type="secondary" style={{ fontSize: 12 }}>
                                     评估结果: ✅ {step.output_data.pass_count || 0} 通过, ❌ {step.output_data.fail_count || 0} 失败
                                   </Text>
                                   {step.output_data.details.map((d, i) => (
                                     <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                                       <Tag color={d.pass ? 'green' : 'red'} style={{ fontSize: 11 }}>
                                         {d.pass ? '✓' : '✗'} {d.id || `#${i+1}`}
                                       </Tag>
                                       <Space size="small" wrap>
                                         <Tag color={d.sharpe >= 1.5 ? 'green' : 'default'}>Sharpe: {d.sharpe?.toFixed(2) ?? '--'}</Tag>
                                         <Tag>Returns: {(d.returns * 100)?.toFixed(1) ?? '--'}%</Tag>
                                         <Tag color={d.turnover <= 0.3 ? 'green' : 'orange'}>Turnover: {d.turnover?.toFixed(2) ?? '--'}</Tag>
                                         <Tag>Fitness: {d.fitness?.toFixed(2) ?? '--'}</Tag>
                                       </Space>
                                     </div>
                                   ))}
                                 </div>
                               )}

                               {/* ROUND_SUMMARY: Show Round Stats & Strategy */}
                               {step.step_type === 'ROUND_SUMMARY' && step.output_data && (
                                 <div style={{ marginTop: 12 }}>
                                   <Row gutter={[12, 12]}>
                                     <Col span={12}>
                                       <div style={{ background: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 4 }}>
                                         <Text type="secondary" style={{ fontSize: 12 }}>本轮战绩</Text>
                                         <div style={{ marginTop: 4 }}>
                                            <Tag color={step.output_data.success_rate > 0 ? "green" : "red"} style={{ marginRight: 4 }}>
                                              {step.output_data.mining_success ? "MINING SUCCESS" : "MINING FAIL"}
                                            </Tag>
                                            <Text style={{ fontSize: 12 }}>
                                              Alphas: {step.output_data.total_alphas} (✅{step.output_data.succeeded_alphas})
                                            </Text>
                                         </div>
                                         <div style={{ marginTop: 4 }}>
                                            <Text style={{ fontSize: 12 }}>
                                              Best Sharpe: <span style={{ color: '#00ff88' }}>{step.output_data.best_sharpe?.toFixed(3) ?? 'N/A'}</span>
                                            </Text>
                                         </div>
                                       </div>
                                     </Col>
                                     <Col span={12}>
                                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 4 }}>
                                          <Text type="secondary" style={{ fontSize: 12 }}>下轮策略 (Adaptive)</Text>
                                          {step.output_data.next_strategy ? (
                                             <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                <div>
                                                  <Tag color="geekblue">Temp: {step.output_data.next_strategy.temperature?.toFixed(1) ?? 'N/A'}</Tag>
                                                  <Text type="secondary" style={{ fontSize: 11 }}>
                                                    ({step.output_data.next_strategy.action})
                                                  </Text>
                                                </div>
                                                <Tag color="purple">Exploration: {step.output_data.next_strategy.exploration_weight?.toFixed(1) ?? 'N/A'}</Tag>
                                             </div>
                                          ) : (
                                            <div style={{ marginTop: 4 }}>
                                              <Text type="secondary" style={{ fontSize: 12 }}>迭代完成或无新策略</Text>
                                            </div>
                                          )}
                                        </div>
                                     </Col>
                                   </Row>
                                 </div>
                               )}
         
                               {/* Legacy single expression display */}
                               {!['ROUND_SUMMARY', 'CODE_GEN'].includes(step.step_type) && !step.output_data?.expressions && (step.output_data?.expression || step.input_data?.expression) && (
                                 <pre style={{ 
                                   marginTop: 8, 
                                   marginBottom: 0,
                                   fontSize: 12,
                                   maxHeight: 100,
                                   overflow: 'auto',
                                   background: '#1f1f1f',
                                   padding: 5
                                 }}>
                                   {step.output_data?.expression || step.input_data?.expression}
                                 </pre>
                               )}
                               
                               {step.error_message && (
                                 <Text type="danger" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                                   ❌ {step.error_message}
                                 </Text>
                               )}
                             </Card>
                           </Timeline.Item>
                         ))}
                       </Timeline>
                   </Panel>
                   )
                })}
              </Collapse>
            ) : (
              <Empty description="暂无轨迹记录" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
