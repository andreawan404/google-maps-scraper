from src.storage.repository import BusinessRepository


def test_upsert_and_exists(repo, sample_business_raw):
    assert not repo.exists(sample_business_raw.place_id)
    repo.upsert(sample_business_raw)
    assert repo.exists(sample_business_raw.place_id)


def test_upsert_is_idempotent(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    repo.upsert(sample_business_raw)  # Tidak boleh error atau duplicate
    stats = repo.get_stats()
    assert stats["total"] == 1


def test_update_email_marks_as_checked(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    pending_before = repo.get_without_email()
    assert len(pending_before) == 1  # website ada, belum dicek

    repo.update_email(sample_business_raw.place_id, "info@apoteksehat.co.id")
    pending_after = repo.get_without_email()
    assert len(pending_after) == 0


def test_update_email_with_none_still_marks_checked(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    repo.update_email(sample_business_raw.place_id, None)  # Tidak ketemu email
    pending = repo.get_without_email()
    assert len(pending) == 0  # email_checked_at sudah diset


def test_update_phone_normalized(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    pending_before = repo.get_without_normalized_phone()
    assert len(pending_before) == 1  # phone ada, belum dinormalisasi

    repo.update_phone_normalized(sample_business_raw.place_id, "+62215551234")
    pending_after = repo.get_without_normalized_phone()
    assert len(pending_after) == 0


def test_get_stats_empty_db(repo):
    stats = repo.get_stats()
    assert stats["total"] == 0
    assert stats["with_email"] == 0
    assert stats["email_coverage"] == "0%"
    assert stats["phone_coverage"] == "0%"


def test_get_stats_with_data(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    repo.update_email(sample_business_raw.place_id, "info@test.co.id")
    stats = repo.get_stats()
    assert stats["total"] == 1
    assert stats["with_email"] == 1
    assert stats["email_coverage"] == "100.0%"


def test_get_all(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    all_records = repo.get_all()
    assert len(all_records) == 1
    assert all_records[0].place_id == sample_business_raw.place_id


def test_mark_enriched(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    repo.mark_enriched(sample_business_raw.place_id)
    all_records = repo.get_all()
    assert all_records[0].enriched is True
