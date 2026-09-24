import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export interface Repository {
  id: string
  github_url: string
  owner?: string
  name?: string
  description?: string
  default_branch?: string
  language?: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface Analysis {
  repository_id: string
  project_summary?: string
  architecture?: string
  setup_guide?: string
  important_files?: Array<{ path: string; purpose: string }>
  technologies?: string[]
  entry_points?: string[]
  dependencies?: string[]
  status: string
}

export interface QuestionResponse {
  repository_id: string
  question: string
  answer?: string
  referenced_files: string[]
  status: string
}

export interface Contribution {
  repository_id: string
  title?: string
  description?: string
  difficulty?: string
  why_suitable?: string
  relevant_files: string[]
  implementation_steps: string[]
  tests_to_add: string[]
  status: string
}

// Repository APIs
export const createRepository = (github_url: string) =>
  api.post<Repository>('/repositories', { github_url }).then((r) => r.data)

export const getRepository = (id: string) =>
  api.get<Repository>(`/repositories/${id}`).then((r) => r.data)

// Analysis APIs
export const startAnalysis = (id: string) =>
  api.post(`/repositories/${id}/analyze`).then((r) => r.data)

export const getAnalysis = (id: string) =>
  api.get<Analysis>(`/repositories/${id}/analysis`).then((r) => r.data)

// Q&A API
export const askQuestion = (id: string, question: string) =>
  api.post<QuestionResponse>(`/repositories/${id}/questions`, { question }).then((r) => r.data)

// Contribution APIs
export const generateContribution = (id: string) =>
  api.post(`/repositories/${id}/contributions/generate`).then((r) => r.data)

export const getContributions = (id: string) =>
  api.get<Contribution>(`/repositories/${id}/contributions`).then((r) => r.data)
