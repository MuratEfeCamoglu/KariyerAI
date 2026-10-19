import { Plus, Trash2 } from "lucide-react";
import { useId } from "react";

import { getFieldError } from "../api/client.ts";
import {
  EDUCATION_LABELS,
  EDUCATION_OPTIONS,
  JOB_LIMITS,
  LANGUAGE_LEVELS,
} from "../lib/constants.ts";
import { fieldBaseClass, selectClass } from "../lib/formStyles.ts";
import type { EducationLevel, JobInput, JobLanguage, LanguageLevel } from "../types/job.ts";
import { Button } from "./Button.tsx";
import { ChipInput } from "./ChipInput.tsx";
import { FieldMessage } from "./FieldMessage.tsx";

/** Puanlamaya giren ilan kriterleri (§3.5); ilan formu ve iş arayan formu ortak kullanır. */
export type CriteriaInput = Pick<
  JobInput,
  "required_skills" | "preferred_skills" | "min_experience_years" | "min_education" | "languages"
>;

interface CriteriaFieldsProps {
  value: CriteriaInput;
  error: unknown;
  onChange: (patch: Partial<CriteriaInput>) => void;
}

export function CriteriaFields({ value, error, onChange }: CriteriaFieldsProps) {
  const experienceId = useId();
  const educationId = useId();
  const fieldError = (field: string) => getFieldError(error, field);
  const set = <K extends keyof CriteriaInput>(key: K, next: CriteriaInput[K]) => {
    onChange({ [key]: next });
  };
  const setLanguage = (index: number, patch: Partial<JobLanguage>) => {
    set(
      "languages",
      value.languages.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    );
  };

  return (
    <>
      <ChipInput
        label="Zorunlu beceriler"
        placeholder="Ör. Python"
        max={JOB_LIMITS.skillsMax}
        value={value.required_skills}
        error={fieldError("required_skills")}
        onChange={(skills) => {
          set("required_skills", skills);
        }}
      />
      <ChipInput
        label="Tercih edilen beceriler"
        placeholder="Ör. Docker"
        max={JOB_LIMITS.skillsMax}
        value={value.preferred_skills}
        error={fieldError("preferred_skills")}
        onChange={(skills) => {
          set("preferred_skills", skills);
        }}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor={experienceId} className="mb-1 block text-sm font-medium text-ink">
            Minimum deneyim (yıl)
          </label>
          <input
            id={experienceId}
            type="number"
            min={0}
            max={JOB_LIMITS.experienceMax}
            step={1}
            value={value.min_experience_years}
            onChange={(event) => {
              set("min_experience_years", event.target.valueAsNumber || 0);
            }}
            className={`${selectClass} ${fieldError("min_experience_years") === undefined ? "border-line-strong" : "border-danger"}`}
          />
          <FieldMessage error={fieldError("min_experience_years")} />
        </div>
        <div>
          <label htmlFor={educationId} className="mb-1 block text-sm font-medium text-ink">
            Minimum eğitim
          </label>
          <select
            id={educationId}
            value={value.min_education}
            onChange={(event) => {
              set("min_education", event.target.value as EducationLevel);
            }}
            className={`${selectClass} border-line-strong`}
          >
            {EDUCATION_OPTIONS.map((level) => (
              <option key={level} value={level}>
                {EDUCATION_LABELS[level]}
              </option>
            ))}
          </select>
          <FieldMessage error={fieldError("min_education")} />
        </div>
      </div>

      <fieldset>
        <div className="mb-1 flex items-baseline justify-between">
          <legend className="text-sm font-medium text-ink">Diller</legend>
          <span className="text-xs text-ink-subtle">
            {value.languages.length}/{JOB_LIMITS.languagesMax}
          </span>
        </div>
        <div className="space-y-2">
          {value.languages.map((item, index) => (
            <div key={index} className="flex gap-2">
              <input
                aria-label={`Dil ${String(index + 1)}`}
                placeholder="Ör. İngilizce"
                value={item.language}
                onChange={(event) => {
                  setLanguage(index, { language: event.target.value });
                }}
                className={`${fieldBaseClass} min-w-0 flex-1 ${getFieldError(error, `languages.${String(index)}`) === undefined ? "border-line-strong" : "border-danger"}`}
              />
              <select
                aria-label={`Dil ${String(index + 1)} seviyesi`}
                value={item.level}
                onChange={(event) => {
                  setLanguage(index, { level: event.target.value as LanguageLevel });
                }}
                className={`${fieldBaseClass} w-24 shrink-0 border-line-strong`}
              >
                {LANGUAGE_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
              <Button
                variant="ghost"
                aria-label={`Dil ${String(index + 1)} kaldır`}
                onClick={() => {
                  set(
                    "languages",
                    value.languages.filter((_, i) => i !== index),
                  );
                }}
              >
                <Trash2 size={16} strokeWidth={1.75} />
              </Button>
            </div>
          ))}
        </div>
        <FieldMessage error={fieldError("languages")} />
        <Button
          variant="secondary"
          size="sm"
          className="mt-2"
          disabled={value.languages.length >= JOB_LIMITS.languagesMax}
          onClick={() => {
            set("languages", [...value.languages, { language: "", level: "B1" }]);
          }}
        >
          <Plus size={16} strokeWidth={1.75} aria-hidden="true" />
          Dil ekle
        </Button>
      </fieldset>
    </>
  );
}
