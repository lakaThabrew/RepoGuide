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

// ---------------------------------------------------------------------------
// Analysis — mirrors backend/app/schemas/analysis.py exactly
// ---------------------------------------------------------------------------

export interface FileEvidence {
  file_path: string
  reason: string
  symbol?: string
  confidence: 'high' | 'medium' | 'low'
  category?: string
}

export interface EntryPoint {
  file_path: string
  kind: string
  symbol?: string
  evidence: string
}

export interface Dependency {
  name: string
  version?: string
  kind: 'runtime' | 'dev' | 'unknown'
  source_file: string
}

export interface RouteEvidence {
  method?: string
  path?: string
  file_path: string
  symbol?: string
  evidence: string
}

export interface ArchitectureComponent {
  name: string
  description: string
  evidence_files: string[]
}

export interface TechnologyFindings {
  languages: string[]
  frameworks: string[]
  runtimes: string[]
  package_managers: string[]
  databases: string[]
  auth_signals: FileEvidence[]
  test_files: string[]
  config_files: string[]
  deployment_files: string[]
  dev_commands: string[]
  api_routes: RouteEvidence[]
  backend_components: string[]
  frontend_components: string[]
  important_directories: string[]
  source_directories: string[]
  test_directories: string[]
  doc_directories: string[]
  arch_components: ArchitectureComponent[]
}

export interface AnalysisResponse {
  id?: string
  repository_id: string
  project_summary?: string
  architecture?: string
  setup_guide?: string
  important_files?: FileEvidence[]
  technologies?: TechnologyFindings
  entry_points?: EntryPoint[]
  dependencies?: Dependency[]
  created_at?: string
}

export interface AnalysisTriggerResponse {
  message: string
  repository_id: string
  status: string
  analysis_id?: string
  evidence_quality?: string
  error?: string
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
  api.post<AnalysisTriggerResponse>(`/repositories/${id}/analyze`).then((r) => r.data)

export const getAnalysis = (id: string) =>
  api.get<AnalysisResponse>(`/repositories/${id}/analysis`).then((r) => r.data)

// Q&A API
export const askQuestion = (id: string, question: string) =>
  api.post<QuestionResponse>(`/repositories/${id}/questions`, { question }).then((r) => r.data)

// Contribution APIs
export const generateContribution = (id: string) =>
  api.post(`/repositories/${id}/contributions/generate`).then((r) => r.data)

export const getContributions = (id: string) =>
  api.get<Contribution>(`/repositories/${id}/contributions`).then((r) => r.data)
