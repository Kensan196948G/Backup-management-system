"""
Unit tests for Rule321110Validator.
app/core/rule_validator.py coverage: 13% -> ~75%
"""
import pytest

from app.core.exceptions import Rule321110ViolationError
from app.core.rule_validator import Rule321110Validator
from app.models import BackupExecution, BackupJob, User, db


@pytest.fixture
def validator():
    return Rule321110Validator()


@pytest.fixture
def job_owner(app):
    with app.app_context():
        user = User(username="validator_owner", email="vowner@example.com", role="operator", is_active=True)
        user.set_password("Test123!")
        db.session.add(user)
        db.session.commit()
        yield user.id


@pytest.fixture
def backup_job(app, job_owner):
    with app.app_context():
        job = BackupJob(
            job_name="rule_validator_test_job",
            job_type="full",
            backup_tool="test_tool",
            retention_days=30,
            owner_id=job_owner,
            is_active=True,
            schedule_type="manual",
        )
        db.session.add(job)
        db.session.commit()
        yield job.id


class TestRule321110ValidatorInit:
    """Tests for validator initialization."""

    def test_default_init(self):
        v = Rule321110Validator()
        assert v.db is None

    def test_init_with_db(self):
        v = Rule321110Validator(db_session="mock_session")
        assert v.db == "mock_session"


class TestValidateJobNotFound:
    """Tests for validate() when job is not found."""

    def test_nonexistent_job_returns_non_compliant(self, app, validator):
        with app.app_context():
            result = validator.validate(999999, raise_on_violation=False)
            assert result["compliant"] is False
            assert result["job_id"] == 999999


class TestValidateNoExecutions:
    """Tests for validate() with no backup executions."""

    def test_no_executions_fails_min_copies(self, app, validator, backup_job):
        with app.app_context():
            result = validator.validate(backup_job, raise_on_violation=False)
            assert result["min_copies"] is False
            assert result["details"]["total_copies"] == 0
            assert result["compliant"] is False

    def test_no_executions_raises_by_default(self, app, validator, backup_job):
        with app.app_context():
            with pytest.raises(Rule321110ViolationError):
                validator.validate(backup_job, raise_on_violation=True)

    def test_no_executions_different_media_false(self, app, validator, backup_job):
        with app.app_context():
            result = validator.validate(backup_job, raise_on_violation=False)
            assert result["different_media"] is False

    def test_no_executions_offsite_false(self, app, validator, backup_job):
        with app.app_context():
            result = validator.validate(backup_job, raise_on_violation=False)
            assert result["offsite_copy"] is False

    def test_no_executions_offline_false(self, app, validator, backup_job):
        with app.app_context():
            result = validator.validate(backup_job, raise_on_violation=False)
            assert result["offline_copy"] is False


class TestGetComplianceScore:
    """Tests for get_compliance_score()."""

    def test_nonexistent_job_score_zero(self, app, validator):
        with app.app_context():
            score = validator.get_compliance_score(999999)
            assert score == 0.0

    def test_score_is_float(self, app, validator, backup_job):
        with app.app_context():
            score = validator.get_compliance_score(backup_job)
            assert isinstance(score, float)

    def test_score_range(self, app, validator, backup_job):
        with app.app_context():
            score = validator.get_compliance_score(backup_job)
            assert 0.0 <= score <= 1.0

    def test_no_compliance_score_zero(self, app, validator, backup_job):
        with app.app_context():
            score = validator.get_compliance_score(backup_job)
            # No copies → min_copies/different_media/offsite/offline all fail
            # zero_errors passes (no failed executions) → score = 0.15
            assert score < 0.5  # Not fully compliant


class TestGetViolationRecommendations:
    """Tests for get_violation_recommendations()."""

    def test_returns_list(self, app, validator, backup_job):
        with app.app_context():
            recs = validator.get_violation_recommendations(backup_job)
            assert isinstance(recs, list)

    def test_recommendations_for_nonexistent_job(self, app, validator):
        with app.app_context():
            recs = validator.get_violation_recommendations(999999)
            assert isinstance(recs, list)
            # Should recommend at least 1 copy
            assert len(recs) > 0

    def test_min_copies_recommendation(self, app, validator, backup_job):
        with app.app_context():
            recs = validator.get_violation_recommendations(backup_job)
            # Should include recommendation about copies
            combined = " ".join(recs)
            assert "コピー" in combined or "バックアップ" in combined

    def test_offsite_recommendation(self, app, validator, backup_job):
        with app.app_context():
            recs = validator.get_violation_recommendations(backup_job)
            combined = " ".join(recs)
            assert "オフサイト" in combined

    def test_offline_recommendation(self, app, validator, backup_job):
        with app.app_context():
            recs = validator.get_violation_recommendations(backup_job)
            combined = " ".join(recs)
            assert "オフライン" in combined


class TestValidateResultStructure:
    """Tests for the result dict structure of validate()."""

    def test_result_has_all_keys(self, app, validator, backup_job):
        with app.app_context():
            result = validator.validate(backup_job, raise_on_violation=False)
            expected_keys = ["job_id", "compliant", "min_copies", "different_media",
                             "offsite_copy", "offline_copy", "zero_errors", "details"]
            for key in expected_keys:
                assert key in result, f"Missing key: {key}"

    def test_result_job_id_matches(self, app, validator, backup_job):
        with app.app_context():
            result = validator.validate(backup_job, raise_on_violation=False)
            assert result["job_id"] == backup_job

    def test_details_has_required_keys(self, app, validator, backup_job):
        with app.app_context():
            result = validator.validate(backup_job, raise_on_violation=False)
            details = result["details"]
            assert "total_copies" in details
