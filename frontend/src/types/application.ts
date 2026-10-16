import type { EducationLevel, JobStatus, LanguageLevel } from "./job.ts";

export type ApplicationStatus =
  "new" | "reviewing" | "shortlisted" | "interview" | "hired" | "rejected";

export type ProcessingStatus = "pending" | "processing" | "done" | "failed";

export type ComponentKey =
  "required_skills" | "experience" | "education" | "languages" | "preferred_skills";

export type ItemPoints = Record<ComponentKey, number>;

export interface ApplicationRow {
  id: number;
  candidate_id: number;
  candidate_name: string | null;
  score: number | null;
  item_points: ItemPoints | null;
  last_position: string | null;
  total_experience_years: number | null;
  status: ApplicationStatus;
  parse_status: ProcessingStatus;
  parse_error: string | null;
  score_status: ProcessingStatus;
  score_error: string | null;
  created_at: string;
}

export interface ApplicationList {
  items: ApplicationRow[];
  total: number;
  page: number;
  page_size: number;
  processing_count: number;
}

export interface ApplicationFilters {
  minScore: number;
  statuses: ApplicationStatus[];
  parseStatus: ProcessingStatus | null;
}

export interface QueuedApplications {
  application_ids: number[];
}

export type EvidenceStatus =
  "verified" | "no_evidence" | "unverified" | "level_unknown" | "level_insufficient";

export interface CriterionResult {
  criterion: string;
  met: boolean;
  status: EvidenceStatus;
  evidence: string | null;
  required_level: LanguageLevel | null;
  candidate_level: LanguageLevel | null;
}

export interface ListComponent {
  weight: number;
  points: number;
  met: number;
  total: number;
  items: CriterionResult[];
}

export interface ExperienceComponent {
  weight: number;
  points: number;
  required_years: number;
  candidate_years: number;
  records: { title: string; company: string | null; start: string | null; end: string | null }[];
}

export interface EducationComponent {
  weight: number;
  points: number;
  required: EducationLevel;
  candidate: EducationLevel | null;
  records: {
    level: EducationLevel;
    field: string | null;
    school: string | null;
    end_year: number | null;
  }[];
}

export interface ScoreBreakdown {
  required_skills: ListComponent;
  experience: ExperienceComponent;
  education: EducationComponent;
  languages: ListComponent;
  preferred_skills: ListComponent;
}

export interface ParsedCV {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  summary: string | null;
  skills: string[];
  experiences: {
    title: string;
    company: string | null;
    start: string | null;
    end: string | null;
    description: string | null;
  }[];
  education: ScoreBreakdown["education"]["records"];
  languages: { language: string; level: LanguageLevel | null }[];
  total_experience_years: number;
}

export interface Note {
  id: number;
  body: string;
  author_id: number;
  author_name: string;
  created_at: string;
}

export interface StatusChange {
  from_status: ApplicationStatus;
  to_status: ApplicationStatus;
  actor_id: number | null;
  actor_name: string | null;
  created_at: string;
}

export interface ApplicationDetail {
  id: number;
  job: { id: number; title: string; status: JobStatus };
  candidate: {
    id: number;
    full_name: string | null;
    email: string | null;
    phone: string | null;
    original_filename: string;
    parse_status: ProcessingStatus;
    parse_error: string | null;
    parsed: ParsedCV | null;
  };
  status: ApplicationStatus;
  score: number | null;
  score_breakdown: ScoreBreakdown | null;
  ai_summary: string | null;
  llm_model: string | null;
  prompt_version: string | null;
  score_status: ProcessingStatus;
  score_error: string | null;
  created_at: string;
  updated_at: string;
  notes: Note[];
  status_history: StatusChange[];
}
