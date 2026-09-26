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

export interface QuestionEvidenceItem {
  file_path: string
  reason?: string
  category?: string
}

export interface QuestionResponse {
  repository_id: string
  question: string
  answer?: string
  evidence: QuestionEvidenceItem[]
  referenced_files: string[]
  is_deterministic: boolean
  intent?: string
  status: string
}

// ---------------------------------------------------------------------------
// Contribution APIs — mirrors backend/app/schemas/contribution.py
// ---------------------------------------------------------------------------

export type ContributionType =
  | 'documentation'
  | 'testing'
  | 'developer_experience'
  | 'maintenance'
  | 'feature'

export type Difficulty = 'beginner' | 'intermediate' | 'advanced'
export type Impact = 'low' | 'medium' | 'high'
export type Confidence = 'high' | 'medium' | 'low'

export interface FileToRead {
  file_path: string
  reason: string
}

export interface ContributionEvidence {
  observation: string
  source: string
}

export interface ContributionCandidate {
  id: string
  title: string
  description: string
  type: ContributionType
  difficulty: Difficulty
  impact: Impact
  confidence: Confidence
  why_good_first_contribution: string
  files_to_read: FileToRead[]
  related_components: string[]
  evidence: ContributionEvidence[]
  suggested_steps: string[]
}

export interface ContributionResponse {
  repository_id: string
  candidates: ContributionCandidate[]
  recommended_ids: string[]
  is_deterministic: boolean
  analysis_id?: string
  generated_at?: string
  evidence_quality?: string
  status: string
  error?: string
}

export interface ContributionGenerateResponse {
  message: string
  repository_id: string
  status: string
  candidates_count?: number
  error?: string
}

// ---------------------------------------------------------------------------
// Setup Guide APIs — mirrors backend/app/schemas/setup.py
// ---------------------------------------------------------------------------

export type SetupConfidence = 'high' | 'medium' | 'low'

export interface SetupCommand {
  command: string
  explanation: string
  evidence: string[]
}

export interface SetupPrerequisite {
  name: string
  version_note: string
  evidence: string[]
}

export interface SetupSection {
  title: string
  description: string
  commands: SetupCommand[]
  notes: string[]
  evidence: string[]
}

export interface SetupWarning {
  message: string
  evidence: string[]
}

export interface SetupGuide {
  repository_id: string
  generated_at?: string
  prerequisites: SetupPrerequisite[]
  install_dependencies?: SetupSection
  environment_configuration?: SetupSection
  database_setup?: SetupSection
  run_application?: SetupSection
  verify_setup?: SetupSection
  confidence: SetupConfidence
  warnings: SetupWarning[]
  is_deterministic: boolean
}

export interface SetupGuideResponse {
  repository_id: string
  guide?: SetupGuide
  status: string
  error?: string
  generated_at?: string
}

export interface SetupGenerateResponse {
  message: string
  repository_id: string
  status: string
  confidence?: string
  warnings_count: number
  error?: string
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
export const generateContributions = (id: string) =>
  api.post<ContributionGenerateResponse>(`/repositories/${id}/contributions/generate`).then((r) => r.data)

export const getContributions = (id: string) =>
  api.get<ContributionResponse>(`/repositories/${id}/contributions`).then((r) => r.data)

// Setup Guide APIs
export const generateSetupGuide = (id: string) =>
  api.post<SetupGenerateResponse>(`/repositories/${id}/setup/generate`).then((r) => r.data)

export const getSetupGuide = (id: string) =>
  api.get<SetupGuideResponse>(`/repositories/${id}/setup`).then((r) => r.data)
