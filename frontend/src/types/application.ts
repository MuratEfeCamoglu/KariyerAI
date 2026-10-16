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
