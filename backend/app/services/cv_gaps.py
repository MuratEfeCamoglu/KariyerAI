"""İş arayan için eksiklik raporu: puan kırılımından kodla, deterministik üretilir.

LLM'e yeni bir iş verilmez. Öneriler adayı sahip olmadığı beceriyi yazmaya yönlendirmez;
dil hep "sahipsen / biliyorsan" biçimindedir.
"""

from app.models.job import EducationLevel
from app.schemas.cv_check import Gap, GapKind
from app.schemas.scoring import CriterionResult, ScoreBreakdown

EDUCATION_ORDER = list(EducationLevel)
EDUCATION_LABELS = {
    EducationLevel.NONE: "Yok",
    EducationLevel.HIGH_SCHOOL: "Lise",
    EducationLevel.ASSOCIATE: "Ön lisans",
    EducationLevel.BACHELOR: "Lisans",
    EducationLevel.MASTER: "Yüksek lisans",
    EducationLevel.PHD: "Doktora",
}


def _skill_message(item: CriterionResult) -> str:
    if item.status == "unverified":
        return (
            f"'{item.criterion}' için gösterilen alıntı CV metninde bulunamadı. "
            "Bu beceriyi kullandığın yeri net bir cümleyle yaz."
        )
    return (
        f"CV'nde '{item.criterion}' kanıtı bulunamadı. Bu beceriye sahipsen, "
        "kullandığın işi veya projeyi açıkça yaz."
    )


def _language_message(item: CriterionResult) -> str:
    if item.status == "level_unknown":
        return (
            f"{item.criterion} seviyen CV'de yazmıyor; seviyeni (ör. {item.required_level}) belirt."
        )
    if item.status == "level_insufficient":
        return (
            f"İlan {item.criterion} için {item.required_level} istiyor, "
            f"CV'nde {item.candidate_level} görünüyor."
        )
    return (
        f"CV'nde {item.criterion} bilgisi bulunamadı. "
        f"Bu dili biliyorsan seviyesiyle (ör. {item.required_level}) ekle."
    )


def _skill_gaps(kind: GapKind, items: list[CriterionResult]) -> list[Gap]:
    return [
        Gap(kind=kind, criterion=item.criterion, status=item.status, message=_skill_message(item))
        for item in items
        if not item.met
    ]


def build_gaps(breakdown: ScoreBreakdown) -> list[Gap]:
    """Sıra önem sırasıdır: zorunlu → deneyim → eğitim → diller → tercih edilen."""
    gaps = _skill_gaps("required_skill", breakdown.required_skills.items)

    experience = breakdown.experience
    if experience.candidate_years < experience.required_years:
        candidate_years = f"{experience.candidate_years:.1f}".replace(".", ",")
        gaps.append(
            Gap(
                kind="experience",
                criterion=f"{experience.required_years} yıl deneyim",
                status="below_requirement",
                message=(
                    f"İlan en az {experience.required_years} yıl deneyim istiyor; CV'nden "
                    f"hesaplanan {candidate_years} yıl. Tarihleri eksik deneyimlerin varsa "
                    "başlangıç ve bitiş tarihlerini ekle."
                ),
            )
        )

    education = breakdown.education
    candidate_rank = EDUCATION_ORDER.index(education.candidate or EducationLevel.NONE)
    if candidate_rank < EDUCATION_ORDER.index(education.required):
        found = (
            f"{EDUCATION_LABELS[education.candidate]} görünüyor"
            if education.candidate is not None
            else "eğitim bilgisi bulunamadı"
        )
        gaps.append(
            Gap(
                kind="education",
                criterion=EDUCATION_LABELS[education.required],
                status="below_requirement",
                message=f"İlan en az {EDUCATION_LABELS[education.required]} istiyor; "
                f"CV'nde {found}.",
            )
        )

    gaps += [
        Gap(
            kind="language",
            criterion=item.criterion,
            status=item.status,
            message=_language_message(item),
        )
        for item in breakdown.languages.items
        if not item.met
    ]
    gaps += _skill_gaps("preferred_skill", breakdown.preferred_skills.items)
    return gaps
