import type { ParsedCV, ProcessingStatus, ScoreBreakdown } from "./application.ts";
import type { EducationLevel, JobLanguage } from "./job.ts";

export interface CvCheckCriteria {
  title: string;
  job_text: string;
  required_skills: string[];
  preferred_skills: string[];
  min_experience_years: number;
  min_education: EducationLevel;
  languages: JobLanguage[];
}

export type GapKind =
  "required_skill" | "experience" | "education" | "language" | "preferred_skill";

export interface Gap {
  kind: GapKind;
  criterion: string;
  status: string;
  message: string;
}

export interface CvCheckListItem {
  id: number;
  title: string;
  original_filename: string;
  score: number | null;
  parse_status: ProcessingStatus;
  score_status: ProcessingStatus;
  created_at: string;
}

export interface CvCheck extends CvCheckListItem, Omit<CvCheckCriteria, "title"> {
  parse_error: string | null;
  score_error: string | null;
  parsed: ParsedCV | null;
  score_breakdown: ScoreBreakdown | null;
  ai_summary: string | null;
  llm_model: string | null;
  prompt_version: string | null;
  gaps: Gap[];
}
