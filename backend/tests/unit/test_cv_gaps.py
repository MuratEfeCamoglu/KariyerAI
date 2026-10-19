from app.models import EducationLevel
from app.schemas.scoring import (
    CriterionResult,
    EducationComponent,
    ExperienceComponent,
    ListComponent,
    ScoreBreakdown,
)
from app.services.cv_gaps import build_gaps


def _list(weight: int, items: list[CriterionResult]) -> ListComponent:
    return ListComponent(
        weight=weight, points=0, met=sum(i.met for i in items), total=len(items), items=items
    )


def _met(name: str) -> CriterionResult:
    return CriterionResult(criterion=name, met=True, status="verified", evidence=name)


def _missing(name: str, **extra: str) -> CriterionResult:
    return CriterionResult(criterion=name, met=False, status="no_evidence", **extra)  # type: ignore[arg-type]


def _breakdown(
    *,
    required: list[CriterionResult] | None = None,
    preferred: list[CriterionResult] | None = None,
    languages: list[CriterionResult] | None = None,
    required_years: int = 0,
    candidate_years: float = 0,
    required_education: EducationLevel = EducationLevel.NONE,
    candidate_education: EducationLevel | None = None,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        required_skills=_list(40, required or [_met("Python")]),
        experience=ExperienceComponent(
            weight=25,
            points=0,
            required_years=required_years,
            candidate_years=candidate_years,
            records=[],
        ),
        education=EducationComponent(
            weight=15,
            points=0,
            required=required_education,
            candidate=candidate_education,
            records=[],
        ),
        languages=_list(10, languages or []),
        preferred_skills=_list(10, preferred or []),
    )


def test_no_gaps_when_all_met() -> None:
    breakdown = _breakdown(
        languages=[
            CriterionResult(
                criterion="English",
                met=True,
                status="verified",
                required_level="B2",
                candidate_level="C1",
            )
        ],
        required_years=3,
        candidate_years=3,
        required_education=EducationLevel.BACHELOR,
        candidate_education=EducationLevel.MASTER,
    )

    assert build_gaps(breakdown) == []


def test_required_skill_no_evidence_message() -> None:
    [gap] = build_gaps(_breakdown(required=[_missing("Docker")]))

    assert gap.kind == "required_skill"
    assert gap.criterion == "Docker"
    assert gap.message == (
        "CV'nde 'Docker' kanıtı bulunamadı. Bu beceriye sahipsen, kullandığın işi veya "
        "projeyi açıkça yaz."
    )


def test_unverified_message() -> None:
    breakdown = _breakdown(
        required=[CriterionResult(criterion="Go", met=False, status="unverified")]
    )

    [gap] = build_gaps(breakdown)

    assert gap.message == (
        "'Go' için gösterilen alıntı CV metninde bulunamadı. Bu beceriyi kullandığın yeri "
        "net bir cümleyle yaz."
    )


def test_experience_gap_partial() -> None:
    [gap] = build_gaps(_breakdown(required_years=5, candidate_years=3.2))

    assert gap.kind == "experience"
    assert gap.message == (
        "İlan en az 5 yıl deneyim istiyor; CV'nden hesaplanan 3,2 yıl. Tarihleri eksik "
        "deneyimlerin varsa başlangıç ve bitiş tarihlerini ekle."
    )


def test_experience_zero_required_no_gap() -> None:
    assert build_gaps(_breakdown(required_years=0, candidate_years=0)) == []


def test_experience_exactly_met_no_gap() -> None:
    assert build_gaps(_breakdown(required_years=2, candidate_years=2.0)) == []


def test_education_one_below() -> None:
    [gap] = build_gaps(
        _breakdown(
            required_education=EducationLevel.BACHELOR,
            candidate_education=EducationLevel.ASSOCIATE,
        )
    )

    assert gap.kind == "education"
    assert gap.message == "İlan en az Lisans istiyor; CV'nde Ön lisans görünüyor."


def test_education_missing() -> None:
    [gap] = build_gaps(_breakdown(required_education=EducationLevel.MASTER))

    assert gap.message == "İlan en az Yüksek lisans istiyor; CV'nde eğitim bilgisi bulunamadı."


def test_language_level_unknown() -> None:
    language = CriterionResult(
        criterion="English", met=False, status="level_unknown", required_level="B2"
    )

    [gap] = build_gaps(_breakdown(languages=[language]))

    assert gap.message == "English seviyen CV'de yazmıyor; seviyeni (ör. B2) belirt."


def test_language_level_insufficient() -> None:
    language = CriterionResult(
        criterion="English",
        met=False,
        status="level_insufficient",
        required_level="C1",
        candidate_level="B1",
    )

    [gap] = build_gaps(_breakdown(languages=[language]))

    assert gap.message == "İlan English için C1 istiyor, CV'nde B1 görünüyor."


def test_language_missing() -> None:
    [gap] = build_gaps(_breakdown(languages=[_missing("German", required_level="B1")]))

    assert gap.message == (
        "CV'nde German bilgisi bulunamadı. Bu dili biliyorsan seviyesiyle (ör. B1) ekle."
    )


def test_order_required_first_preferred_last() -> None:
    breakdown = _breakdown(
        required=[_missing("X")],
        preferred=[_missing("Y")],
        languages=[_missing("Z", required_level="B1")],
        required_years=3,
        candidate_years=1,
        required_education=EducationLevel.BACHELOR,
    )

    kinds = [gap.kind for gap in build_gaps(breakdown)]

    assert kinds == ["required_skill", "experience", "education", "language", "preferred_skill"]
