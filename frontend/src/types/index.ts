/**
 * Shared TypeScript types for the RepoGuide frontend.
 *
 * This module re-exports the primary domain interfaces from the API service
 * so that page and component files can import from a single, stable location.
 *
 * The canonical interface definitions live in ../services/api because they
 * are defined alongside the API functions that produce them. This barrel
 * exists for convenience and future centralisation.
 */

export type {
  Repository,
  FileEvidence,
  EntryPoint,
  Dependency,
  RouteEvidence,
  ArchitectureComponent,
  ArchitectureRelationship,
  ArchitectureData,
  ArchitectureResponse,
  TechnologyFindings,
  AnalysisResponse,
  AnalysisTriggerResponse,
  QuestionEvidenceItem,
  QuestionSourceFile,
  QuestionResponse,
  ContributionType,
  Difficulty,
  Impact,
  Confidence,
  FileToRead,
  ContributionEvidence,
  ContributionCandidate,
  ContributionResponse,
  ContributionGenerateResponse,
  SetupConfidence,
  SetupCommand,
  SetupPrerequisite,
  SetupSection,
  SetupWarning,
  SetupGuide,
  SetupGuideResponse,
  SetupGenerateResponse,
  RepositoryFileItem,
  RepositoryFileTree,
  FileContentResponse,
} from '../services/api'
