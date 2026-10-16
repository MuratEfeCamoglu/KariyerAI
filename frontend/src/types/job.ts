export type JobStatus = "open" | "closed";

export type EducationLevel = "none" | "high_school" | "associate" | "bachelor" | "master" | "phd";

export type LanguageLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

export interface JobLanguage {
  language: string;
  level: LanguageLevel;
}

export interface JobInput {
  title: string;
  department: string;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  min_experience_years: number;
  min_education: EducationLevel;
  languages: JobLanguage[];
  status: JobStatus;
}

export interface Job extends JobInput {
  id: number;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface JobListItem extends Job {
  application_count: number;
  top_score: number | null;
  avg_score: number | null;
}
