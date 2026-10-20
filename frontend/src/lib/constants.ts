import type { ApplicationStatus, EvidenceStatus, ProcessingStatus } from "../types/application.ts";
import type { EducationLevel, JobStatus, LanguageLevel } from "../types/job.ts";
import type { UserRole } from "../types/user.ts";

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Admin",
  recruiter: "İK Uzmanı",
  seeker: "İş arayan",
};

/** Giriş sonrası ve bilinmeyen adreslerde rolün ana sayfası. */
export function homePathFor(role: UserRole): string {
  if (role === "seeker") return "/cv-checks";
  return role === "admin" ? "/users" : "/jobs";
}

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

/** ISKELET.md F4 yükleme sınırları; backend doğrulamasıyla aynı tutulur. */
export const UPLOAD_LIMITS = {
  maxFiles: 20,
  maxFileBytes: 5 * 1024 * 1024,
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

export const SEEKER_DISCLAIMER =
  "Bu değerlendirme yapay zekâ desteklidir; işverenlerin değerlendirmesi farklı olabilir.";

export const APPLICATION_STATUS_OPTIONS: ApplicationStatus[] = [
  "new",
  "reviewing",
  "shortlisted",
  "interview",
  "hired",
  "rejected",
];

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  new: "Yeni",
  reviewing: "İnceleniyor",
  shortlisted: "Kısa liste",
  interview: "Mülakat",
  hired: "İşe alındı",
  rejected: "Reddedildi",
};

/** TASARIM.md §2; "Mülakat" için #F5F3FF/#5B21B6 = Tailwind tema token'ları violet-50/violet-800. */
export const APPLICATION_STATUS_CLASSES: Record<ApplicationStatus, string> = {
  new: "bg-info-bg text-info",
  reviewing: "bg-brand-50 text-brand-700",
  shortlisted: "bg-accent-50 text-accent-700",
  interview: "bg-violet-50 text-violet-800",
  hired: "bg-band-high-bg text-band-high-text",
  rejected: "bg-fill-muted text-ink-muted",
};

export const PROCESSING_STATUS_LABELS: Record<ProcessingStatus, string> = {
  pending: "Kuyrukta",
  processing: "İşleniyor",
  done: "Tamamlandı",
  failed: "Başarısız",
};

export const PROCESSING_STATUS_OPTIONS: ProcessingStatus[] = [
  "pending",
  "processing",
  "done",
  "failed",
];

/** ISKELET B3: her kalem ya doğrulanmış kanıt ya da açık bir ibare gösterir. */
export const EVIDENCE_STATUS_LABELS: Record<EvidenceStatus, string> = {
  verified: "Kanıt doğrulandı",
  no_evidence: "Kanıt bulunamadı",
  unverified: "Kanıt doğrulanamadı",
  level_unknown: "Seviye belirtilmemiş",
  level_insufficient: "Seviye yetersiz",
};

/** Denetim kaydı eylemleri (F12); bilinmeyen eylem kendi koduyla gösterilir. */
export const AUDIT_ACTION_LABELS: Record<string, string> = {
  "auth.login": "Giriş",
  "user.create": "Kullanıcı oluşturma",
  "user.update": "Kullanıcı güncelleme",
  "user.approve": "Hesap onaylandı",
  "user.reject": "Hesap reddedildi",
  "job.create": "İlan oluşturma",
  "job.update": "İlan güncelleme",
  "job.delete": "İlan silme",
  "job.rescore": "Yeniden puanlama",
  "cv.upload": "CV yükleme",
  "cv.parse": "Ayrıştırma sonucu",
  "score.result": "Puanlama sonucu",
  "application.status": "Durum değişikliği",
  "application.retry": "Yeniden deneme",
  "candidate.delete": "Aday silme",
  "cv_check.create": "CV değerlendirme oluşturma",
  "cv_check.parse": "CV değerlendirme ayrıştırma",
  "cv_check.score": "CV değerlendirme puanlama",
  "cv_check.retry": "CV değerlendirme yeniden deneme",
  "cv_check.delete": "CV değerlendirme silme",
};
