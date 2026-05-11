import axios from 'axios'

const API_BASE = '/api/v1'

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// API functions
const api = {
  // Datasets & Fields
  getDatasets: async (params = {}) => {
    const { data } = await client.get('/datasets', { params })
    return data
  },

  getDataset: async (id) => {
    const { data } = await client.get(`/datasets/${id}`)
    return data
  },

  syncDatasets: async (region, universe) => {
    const { data } = await client.post('/datasets/sync', null, { params: { region, universe } })
    return data
  },

  getDatasetCategories: async () => {
    const { data } = await client.get('/datasets/categories')
    return data
  },

  getDatasetFields: async (datasetId, params = {}) => {
    const { data } = await client.get(`/datasets/${datasetId}/fields`, { params })
    return data
  },

  syncDatasetFields: async (datasetId, region, universe) => {
    const { data } = await client.post(`/datasets/${datasetId}/sync-fields`, null, { 
      params: { region, universe } 
    })
    return data
  },

  // Operators
  getOperators: async (params = {}) => {
    const { data } = await client.get('/operators', { params })
    return data
  },

  syncOperators: async () => {
    const { data } = await client.post('/operators/sync')
    return data
  },

  // Dashboard / Stats
  getDailyStats: async (date) => {
    const params = date ? { date } : {}
    const { data } = await client.get('/stats/daily', { params })
    return data
  },

  getKPIMetrics: async () => {
    const { data } = await client.get('/stats/kpi')
    return data
  },

  getActiveTasks: async () => {
    const { data } = await client.get('/stats/active-tasks')
    return data
  },

  // Tasks
  getTasks: async (params = {}) => {
    const { data } = await client.get('/tasks', { params })
    return data
  },

  getTask: async (id) => {
    const { data } = await client.get(`/tasks/${id}`)
    return data
  },

  getTaskTrace: async (id) => {
    const { data } = await client.get(`/tasks/${id}/trace`)
    return data
  },

  createTask: async (taskData) => {
    const { data } = await client.post('/tasks', taskData)
    return data
  },

  startTask: async (id) => {
    const { data } = await client.post(`/tasks/${id}/start`)
    return data
  },

  interveneTask: async (id, action, parameters = {}) => {
    const { data } = await client.post(`/tasks/${id}/intervene`, { action, parameters })
    return data
  },

  getTaskRuns: async (taskId) => {
    const { data } = await client.get(`/tasks/${taskId}/runs`)
    return data
  },

  getRun: async (runId) => {
    const { data } = await client.get(`/runs/${runId}`)
    return data
  },

  getRunTrace: async (runId) => {
    const { data } = await client.get(`/runs/${runId}/trace`)
    return data
  },

  getRunAlphas: async (runId, params = {}) => {
    const { data } = await client.get(`/runs/${runId}/alphas`, { params })
    return data
  },

  // Alphas
  getAlphas: async (params = {}) => {
    const { data } = await client.get('/alphas', { params })
    return data
  },

  getAlpha: async (id) => {
    const { data } = await client.get(`/alphas/${id}`)
    return data
  },

  getAlphaTrace: async (id) => {
    const { data } = await client.get(`/alphas/${id}/trace`)
    return data
  },

  submitAlphaFeedback: async (id, rating, comment = null) => {
    const { data } = await client.post(`/alphas/${id}/feedback`, { rating, comment })
    return data
  },

  syncAlphas: async () => {
    const { data } = await client.post('/alphas/sync')
    return data
  },

  // Knowledge
  getKnowledgeEntries: async (params = {}) => {
    const { data } = await client.get('/knowledge', { params })
    return data
  },

  getSuccessPatterns: async (limit = 20) => {
    const { data } = await client.get('/knowledge/success-patterns', { params: { limit } })
    return data
  },

  getFailurePitfalls: async (limit = 50) => {
    const { data } = await client.get('/knowledge/failure-pitfalls', { params: { limit } })
    return data
  },

  createKnowledgeEntry: async (entryData) => {
    const { data } = await client.post('/knowledge', entryData)
    return data
  },

  updateKnowledgeEntry: async (id, updates) => {
    const { data } = await client.put(`/knowledge/${id}`, updates)
    return data
  },

  deleteKnowledgeEntry: async (id) => {
    const { data } = await client.delete(`/knowledge/${id}`)
    return data
  },

  // Config
  getConfig: async () => {
    const { data } = await client.get('/config')
    return data
  },

  getThresholds: async () => {
    const { data } = await client.get('/config/thresholds')
    return data
  },

  updateThresholds: async (thresholds) => {
    const { data } = await client.put('/config/thresholds', thresholds)
    return data
  },

  updateDiversity: async (diversity) => {
    const { data } = await client.put('/config/diversity', diversity)
    return data
  },

  // Credentials Management
  getCredentialsStatus: async () => {
    const { data } = await client.get('/config/credentials')
    return data
  },

  setBrainCredentials: async (email, password) => {
    const { data } = await client.post('/config/credentials/brain', { email, password })
    return data
  },

  setLLMCredentials: async (apiKey, baseUrl, model) => {
    const { data } = await client.post('/config/credentials/llm', { 
      api_key: apiKey, 
      base_url: baseUrl, 
      model 
    })
    return data
  },

  testBrainCredentials: async () => {
    const { data } = await client.post('/config/credentials/brain/test')
    return data
  },

  deleteCredential: async (key) => {
    const { data } = await client.delete(`/config/credentials/${key}`)
    return data
  },
}

export default api
