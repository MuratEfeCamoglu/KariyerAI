from app.services.anonymizer import MASK, anonymize

CV = """Deniz Arslan
deniz.arslan@example.com | +90 555 000 11 22 | linkedin.com/in/denizarslan
Adres: Örnek Mah. Deneme Sok. No:5 Kadıköy/İstanbul
Address: 221B Sample Street
Doğum Tarihi: 12.03.1990
Cinsiyet: Kadın
Portfolyo: https://denizarslan.dev/projeler
Senior Backend Developer (2021-03 – present)
Built Python services. Contact D. Arslan at (0555) 000-33-44.
Deniz taşımacılığı projelerinde çalıştı. Referans: Arslan ailesi değil.
"""


def test_removes_name_contact_and_address_lines() -> None:
    result = anonymize(CV, "Deniz Arslan")

    for leaked in (
        "Deniz",
        "Arslan",
        "deniz.arslan@example.com",
        "555 000 11 22",
        "000-33-44",
        "linkedin.com",
        "denizarslan.dev",
        "Örnek Mah",
        "221B",
        "12.03.1990",
        "Kadın",
    ):
        assert leaked.casefold() not in result.casefold(), leaked
    assert "Adres" not in result and "Address" not in result


def test_keeps_professional_content_and_experience_dates() -> None:
    result = anonymize(CV, "Deniz Arslan")

    assert "Senior Backend Developer (2021-03 – present)" in result
    assert "Built Python services." in result
    assert "Doğum Tarihi: " + MASK in result


def test_without_name_still_masks_contact_data() -> None:
    result = anonymize("Ad Soyad\nali@example.com\n+90 555 000 11 22\nSkills: SQL", None)

    assert "ali@example.com" not in result
    assert "555" not in result
    assert "Skills: SQL" in result


def test_is_deterministic() -> None:
    assert anonymize(CV, "Deniz Arslan") == anonymize(CV, "Deniz Arslan")
