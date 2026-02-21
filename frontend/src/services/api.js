import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const startRun = (brief) => api.post('/runs', { brief })
export const getRun = (id) => api.get(`/runs/${id}`)
export const listRuns = () => api.get('/runs')
export const getArtifacts = (id) => api.get(`/runs/${id}/artifacts`)
export const getGeneratedFiles = (id) => api.get(`/runs/${id}/files`)
export const getFileContent = (id, path) => api.get(`/runs/${id}/files/${path}`)
export const getDecisionsLog = (id) => api.get(`/runs/${id}/decisions`)
export const getActivityLog = (id) => api.get(`/runs/${id}/activity`)
export const submitHITL = (id, decision, feedback) => api.post(`/runs/${id}/hitl`, { decision, feedback })
export const exportProject = (id) => api.post(`/runs/${id}/export`)
export const deployApp = (anthropicApiKey) => api.post('/deploy', { anthropic_api_key: anthropicApiKey || '' })
export const teardownApp = () => api.post('/teardown')
export const deployStatus = () => api.get('/deploy/status')
export const deployCheck = () => api.get('/deploy/check')
export const getAgents = () => api.get('/agents')
export const getGraph = () => api.get('/graph')

export default api
