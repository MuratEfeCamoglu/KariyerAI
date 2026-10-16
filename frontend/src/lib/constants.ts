import type { EducationLevel, JobStatus, LanguageLevel } from "../types/job.ts";
import type { UserRole } from "../types/user.ts";

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Admin",
  recruiter: "İK Uzmanı",
};

export const ROLE_OPTIONS: UserRole[] = ["recruiter", "admin"];

export const MIN_PASSWORD_LENGTH = 10;

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  open: "Açık",
  closed: "Kapalı",
};

export const EDUCATION_LABELS: Record<EducationLevel, string> = {
  none: "Yok",
  high_school: "Lise",
  associate: "Ön lisans",
  bachelor: "Lisans",
  master: "Yüksek lisans",
  phd: "Doktora",
};

export const EDUCATION_OPTIONS: EducationLevel[] = [
  "none",
  "high_school",
  "associate",
  "bachelor",
  "master",
  "phd",
];

export const LANGUAGE_LEVELS: LanguageLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];

/** ISKELET.md F3 alan sınırları; backend doğrulamasıyla aynı tutulur. */
export const JOB_LIMITS = {
  titleMax: 120,
  departmentMax: 100,
  descriptionMax: 5000,
  skillsMax: 20,
  languagesMax: 5,
  experienceMax: 40,
} as const;

/** ISKELET.md §3.5 sabit ağırlıklar (V6). */
export const SCORE_WEIGHTS = [
  { key: "required_skills", label: "Zorunlu beceriler", weight: 40 },
  { key: "experience", label: "Deneyim", weight: 25 },
  { key: "education", label: "Eğitim", weight: 15 },
  { key: "languages", label: "Diller", weight: 10 },
  { key: "preferred_skills", label: "Tercih edilen", weight: 10 },
] as const;

export type ScoreBand = "high" | "mid" | "low";

export const SCORE_BAND_LABELS: Record<ScoreBand, string> = {
  high: "Yüksek uyum",
  mid: "Orta uyum",
  low: "Düşük uyum",
};

/** ISKELET.md §3.5: ≥ 75 yüksek, 50–74 orta, < 50 düşük. */
export function scoreBand(score: number): ScoreBand {
  if (score >= 75) return "high";
  if (score >= 50) return "mid";
  return "low";
}

export const AI_DISCLAIMER = "Bu puan bir öneridir; karar İK uzmanına aittir.";
