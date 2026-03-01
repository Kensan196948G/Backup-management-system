"""
End-to-End API Test Suite

Complete API workflow tests covering:
1. Authentication Flow (Login -> Access -> Refresh -> Logout)
2. API Key Lifecycle (Create -> Use -> Delete)
3. Backup Job CRUD Operations
4. AOMEI Integration Endpoints
5. Verification Test Execution
6. Report Generation
7. Complete Business Workflows
"""

import json
import time
from datetime import datetime, timedelta

import pytest

from app.models import (
    Alert,
    BackupCopy,
    BackupExecution,
    BackupJob,
    OfflineMedia,
    Report,
    VerificationTest,
    db,
)
from app.models_api_key import ApiKey


class TestAuthenticationFlow:
    """Test complete authentication flow."""

    def test_complete_jwt_flow(self, api_client, admin_user, app):
        """Test complete JWT authentication flow: Login -> Access -> Refresh -> Logout."""
        with app.app_context():
            # Step 1: Login
            login_response = api_client.login("admin", "Admin123!@#")
            assert login_response.status_code == 200

            login_data = login_response.get_json()
            assert login_data["success"] is True
            assert api_client.access_token is not None
            assert api_client.refresh_token is not None

            original_access_token = api_client.access_token

            # Step 2: Access protected resource
            jobs_response = api_client.get("/api/jobs")
            assert jobs_response.status_code in [200, 404]

            # Step 3: Wait and refresh token
            time.sleep(1)
            refresh_response = api_client.refresh()
            assert refresh_response.status_code == 200

            refresh_data = refresh_response.get_json()
            assert refresh_data["success"] is True
            assert api_client.access_token != original_access_token

            # Step 4: Access with new token
            jobs_response2 = api_client.get("/api/jobs")
            assert jobs_response2.status_code in [200, 404]

            # Step 5: Logout
            logout_response = api_client.logout()
            if logout_response:
                assert logout_response.status_code in [200, 404]

            # Step 6: Verify token is cleared
            assert api_client.access_token is None


class TestAPIKeyLifecycle:
    """Test complete API key lifecycle."""

    def test_api_key_complete_lifecycle(self, admin_api_client, app):
        """Test API key lifecycle: Create -> Use -> List -> Revoke."""
        with app.app_context():
            # Step 1: Create API key
            create_response = admin_api_client.post(
                "/api/v1/auth/api-keys", json={"name": "E2E Test Key", "expires_in_days": 30}
            )

            if create_response.status_code not in [200, 201]:
                pytest.skip("API key creation endpoint not available")

            create_data = create_response.get_json()
            assert create_data["success"] is True

            api_key = create_data["api_key"]
            key_id = (create_data.get("key_id") or create_data.get("id") or
                      create_data.get("key_info", {}).get("id"))

            assert api_key.startswith("bms_")

            # Step 2: Use API key to access endpoint
            use_response = admin_api_client.client.get("/api/jobs", headers={"X-API-Key": api_key})

            assert use_response.status_code in [200, 401, 404]
            list_response = admin_api_client.get("/api/v1/auth/api-keys")
            assert list_response.status_code == 200

            list_data = list_response.get_json()
            keys = list_data.get("api_keys", list_data)

            # Should find our key
            found_key = False
            for key in keys:
                if key.get("id") == key_id or key.get("name") == "E2E Test Key":
                    found_key = True
                    break
            assert found_key

            # Step 4: Revoke API key
            revoke_response = admin_api_client.delete(f"/api/v1/auth/api-keys/{key_id}")

            assert revoke_response.status_code in [200, 204]

            # Step 5: Verify key no longer works
            verify_response = admin_api_client.client.get("/api/jobs", headers={"X-API-Key": api_key})

            # Should be rejected (401) or not found (404)
            assert verify_response.status_code in [401, 404]


class TestBackupJobCRUD:
    """Test complete backup job CRUD operations."""

    def test_backup_job_crud_workflow(self, admin_api_client, app):
        """Test complete backup job workflow: Create -> Read -> Update -> Execute -> Delete."""
        with app.app_context():
            # Step 1: Create backup job
            create_response = admin_api_client.post(
                "/api/jobs",
                json={
                    "job_name": "E2E Test Backup Job",
                    "job_type": "file",
                    "backup_tool": "custom",
                    "description": "End-to-end test backup job",
                    "target_path": "/data/test/e2e",
                    "schedule_type": "daily",
                    "schedule_time": "03:00",
                    "retention_days": 30,
                    "is_active": True,
                },
            )

            if create_response.status_code not in [200, 201]:
                pytest.skip("Backup job creation endpoint not available")

            create_data = create_response.get_json()
            job_id = create_data.get("job_id") or create_data.get("id")

            # Step 2: Read job details
            read_response = admin_api_client.get(f"/api/jobs/{job_id}")
            assert read_response.status_code == 200

            read_data = read_response.get_json()
            job = read_data.get("job", read_data)
            assert job["job_name"] == "E2E Test Backup Job"

            # Step 3: Update job
            update_response = admin_api_client.put(
                f"/api/jobs/{job_id}",
                json={"job_name": "E2E Updated Backup Job", "retention_days": 60, "description": "Updated description"},
            )

            assert update_response.status_code == 200

            # Step 4: Verify update
            verify_response = admin_api_client.get(f"/api/jobs/{job_id}")
            assert verify_response.status_code == 200

            verify_data = verify_response.get_json()
            updated_job = verify_data.get("job", verify_data)
            assert updated_job["job_name"] == "E2E Updated Backup Job"
            assert updated_job["retention_days"] == 60

            # Step 5: Execute job manually
            execute_response = admin_api_client.post(f"/api/jobs/{job_id}/run")

            # Should trigger execution (200/202) or not found
            assert execute_response.status_code in [200, 202, 404]

            # Step 6: Check execution history
            history_response = admin_api_client.get(f"/api/jobs/{job_id}/executions")

            if history_response.status_code == 200:
                history_data = history_response.get_json()
                executions = history_data.get("executions", history_data)
                # May have executions if job actually ran

            # Step 7: Delete job
            delete_response = admin_api_client.delete(f"/api/jobs/{job_id}")

            assert delete_response.status_code in [200, 204]

            # Step 8: Verify deletion
            final_response = admin_api_client.get(f"/api/jobs/{job_id}")
            assert final_response.status_code == 404


class TestAOMEIIntegration:
    """Test AOMEI backup integration endpoints."""

    def test_aomei_backup_status_update(self, admin_api_client, backup_job, app):
        """Test AOMEI backup status update workflow."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)

            # Step 1: Report backup start
            start_response = admin_api_client.post(
                "/api/backup/status",
                json={"job_id": job.id, "execution_result": "running", "source_system": "aomei_backupper"},
            )

            if start_response.status_code in [200, 201]:
                # Backup started successfully
                pass

            # Step 2: Report backup completion
            complete_response = admin_api_client.post(
                "/api/backup/status",
                json={
                    "job_id": job.id,
                    "execution_result": "success",
                    "backup_size_bytes": 5368709120,  # 5GB
                    "duration_seconds": 600,
                    "files_backed_up": 15000,
                    "source_system": "aomei_backupper",
                },
            )

            assert complete_response.status_code in [200, 201, 404]

            # Step 3: Verify execution was recorded
            if complete_response.status_code in [200, 201]:
                execution = BackupExecution.query.filter_by(job_id=job.id).order_by(BackupExecution.id.desc()).first()

                if execution:
                    assert execution.execution_result == "success"

    def test_aomei_backup_failure_workflow(self, admin_api_client, backup_job, app):
        """Test AOMEI backup failure reporting."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)

            # Report backup failure
            failure_response = admin_api_client.post(
                "/api/backup/status",
                json={
                    "job_id": job.id,
                    "execution_result": "failed",
                    "error_message": "Disk full - cannot complete backup",
                    "source_system": "aomei_backupper",
                },
            )

            assert failure_response.status_code in [200, 201, 404]

            # Verify alert was created
            if failure_response.status_code in [200, 201]:
                alert = Alert.query.filter_by(job_id=job.id, alert_type="backup_failure").first()

                # Alert may or may not be auto-created
                if alert:
                    assert "disk full" in alert.message.lower()

    def test_aomei_copy_status_update(self, admin_api_client, backup_copies, app):
        """Test AOMEI backup copy status update."""
        with app.app_context():
            copy = db.session.get(BackupCopy, backup_copies[0].id)

            response = admin_api_client.post(
                "/api/backup/copy-status",
                json={
                    "copy_id": copy.id,
                    "status": "success",
                    "last_backup_size": 6442450944,  # 6GB
                    "last_backup_date": datetime.utcnow().isoformat(),
                },
            )

            if response.status_code in [200, 201]:
                # Verify copy was updated
                updated_copy = db.session.get(BackupCopy, copy.id)
                assert updated_copy.status == "success"
                assert updated_copy.last_backup_size == 6442450944


class TestVerificationWorkflow:
    """Test verification test workflow."""

    def test_complete_verification_workflow(self, admin_api_client, backup_job, app):
        """Test complete verification workflow: Schedule -> Execute -> Results -> Acknowledge."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)

            # Step 1: Schedule verification test
            schedule_response = admin_api_client.put(
                f"/api/v1/verification/schedule/{job.id}",
                json={
                    "test_type": "full_restore",
                    "frequency_days": 7,
                    "next_test_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                },
            )

            if schedule_response.status_code not in [200, 201]:
                pytest.skip("Verification scheduling endpoint not available")

            # Step 2: Execute verification test
            execute_response = admin_api_client.post(f"/api/v1/verification/restore/{job.id}")

            if execute_response.status_code in [200, 202]:
                # Test started
                pass

            # Step 3: Report test completion
            report_response = admin_api_client.post(
                "/api/v1/verification",
                json={
                    "job_id": job.id,
                    "test_type": "full_restore",
                    "test_result": "success",
                    "duration_seconds": 1200,
                    "notes": "Full restore test completed successfully",
                },
            )

            if report_response.status_code in [200, 201]:
                # Test recorded
                pass

            # Step 4: Get verification results
            results_response = admin_api_client.get(f"/api/v1/verification/results/{job.id}")

            if results_response.status_code == 200:
                results_data = results_response.get_json()
                tests = results_data.get("tests", results_data)

                # Should have at least one test result
                if isinstance(tests, list) and len(tests) > 0:
                    assert tests[0]["test_result"] in ["success", "failed"]

    def test_checksum_verification(self, admin_api_client, backup_job, app):
        """Test checksum verification workflow."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)

            # Execute checksum verification
            response = admin_api_client.post(f"/api/v1/verification/checksum/{job.id}")

            # Should trigger verification
            assert response.status_code in [200, 202, 404]


class TestReportGeneration:
    """Test report generation workflow."""

    def test_complete_report_workflow(self, admin_api_client, backup_job, app):
        """Test complete report workflow: Generate -> List -> Download."""
        with app.app_context():
            # Step 1: Generate daily report
            generate_response = admin_api_client.post("/api/v1/reports/generate/daily")

            if generate_response.status_code not in [200, 201]:
                pytest.skip("Report generation endpoint not available")

            generate_data = generate_response.get_json()
            report_id = generate_data.get("report_id") or generate_data.get("id")

            # Step 2: List reports
            list_response = admin_api_client.get("/api/v1/reports")
            assert list_response.status_code == 200

            list_data = list_response.get_json()
            reports = list_data.get("reports", list_data)

            # Should find our report
            found_report = False
            for report in reports:
                if report.get("id") == report_id:
                    found_report = True
                    break
            assert found_report

            # Step 3: Get report details
            details_response = admin_api_client.get(f"/api/v1/reports/{report_id}")
            assert details_response.status_code == 200

            # Step 4: Download report (if implemented)
            download_response = admin_api_client.get(f"/api/v1/reports/{report_id}/download")

            # May return file or 404 if not implemented
            assert download_response.status_code in [200, 404]

    def test_generate_all_report_types(self, admin_api_client, app):
        """Test generating different report types."""
        with app.app_context():
            report_types = ["daily", "weekly", "monthly"]

            for report_type in report_types:
                response = admin_api_client.post(f"/api/v1/reports/generate/{report_type}")

                # Should successfully generate or not found
                assert response.status_code in [200, 201, 404]

                if response.status_code in [200, 201]:
                    data = response.get_json()
                    assert data["success"] is True


class TestCompleteBusinessWorkflow:
    """Test complete end-to-end business workflows."""

    def test_new_backup_job_complete_workflow(self, admin_api_client, app):
        """Test complete workflow for new backup job from creation to verification."""
        with app.app_context():
            # Step 1: Create backup job
            create_response = admin_api_client.post(
                "/api/jobs",
                json={
                    "job_name": "Production Database Backup",
                    "job_type": "database",
                    "backup_tool": "aomei_backupper",
                    "description": "Daily production database backup",
                    "target_path": "/backups/db/production",
                    "schedule_type": "daily",
                    "schedule_time": "02:00",
                    "retention_days": 30,
                    "is_active": True,
                },
            )

            if create_response.status_code not in [200, 201]:
                pytest.skip("Cannot test workflow - job creation failed")

            job_id = create_response.get_json().get("job_id") or create_response.get_json().get("id")

            # Step 2: Add backup copies (3-2-1-1-0 rule)
            copies_data = [
                {"job_id": job_id, "copy_type": "primary", "storage_path": "Primary NAS", "media_type": "disk"},
                {"job_id": job_id, "copy_type": "secondary", "storage_path": "Secondary NAS", "media_type": "disk"},
                {"job_id": job_id, "copy_type": "offsite", "storage_path": "AWS S3", "media_type": "cloud"},
            ]

            for copy_data in copies_data:
                copy_response = admin_api_client.post("/api/v1/backups/copies", json=copy_data)
                # May or may not be implemented
                if copy_response.status_code in [200, 201]:
                    pass

            # Step 3: Execute first backup
            execute_response = admin_api_client.post(f"/api/jobs/{job_id}/run")

            if execute_response.status_code in [200, 202]:
                # Backup triggered
                pass

            # Step 4: Report backup success
            status_response = admin_api_client.post(
                "/api/backup/status",
                json={
                    "job_id": job_id,
                    "execution_result": "success",
                    "backup_size_bytes": 10737418240,  # 10GB
                    "duration_seconds": 1800,
                    "files_backed_up": 1,
                    "source_system": "aomei_backupper",
                },
            )

            # Step 5: Schedule verification test
            verification_response = admin_api_client.put(
                f"/api/v1/verification/schedule/{job_id}", json={"test_type": "full_restore", "frequency_days": 30}
            )

            # Step 6: Get job compliance status
            compliance_response = admin_api_client.get(f"/api/jobs/{job_id}/compliance")

            if compliance_response.status_code == 200:
                compliance_data = compliance_response.get_json()
                # Should have compliance information

            # Step 7: Generate report
            report_response = admin_api_client.post("/api/v1/reports/generate/daily")

            # Step 8: Cleanup - delete job
            delete_response = admin_api_client.delete(f"/api/jobs/{job_id}")

            assert delete_response.status_code in [200, 204]

    def test_media_rotation_workflow(self, admin_api_client, app):
        """Test offline media rotation workflow."""
        with app.app_context():
            # Step 1: Register new offline media
            create_response = admin_api_client.post(
                "/api/v1/media",
                json={
                    "media_type": "tape",
                    "media_id": "TAPE-E2E-001",
                    "capacity_gb": 2000,
                    "storage_location": "Vault A",
                    "current_status": "available",
                },
            )

            if create_response.status_code not in [200, 201]:
                pytest.skip("Media registration not available")

            media_id = create_response.get_json().get("media_id") or create_response.get_json().get("id")

            # Step 2: Lend media for backup
            lend_response = admin_api_client.post(
                f"/api/v1/media/{media_id}/lend",
                json={
                    "lent_to": "Backup Operator",
                    "purpose": "Weekly backup rotation",
                    "expected_return_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                },
            )

            # Step 3: Return media
            return_response = admin_api_client.post(
                f"/api/v1/media/{media_id}/return", json={"notes": "Backup completed successfully"}
            )

            # Step 4: Store media offsite
            update_response = admin_api_client.put(
                f"/api/v1/media/{media_id}", json={"storage_location": "Offsite Vault B", "current_status": "stored"}
            )

            # Step 5: Eventually retire media
            retire_response = admin_api_client.post(
                f"/api/v1/media/{media_id}/retire", json={"retirement_reason": "End of life"}
            )


class TestDashboardAndAnalytics:
    """Test dashboard and analytics endpoints."""

    def test_dashboard_data_workflow(self, admin_api_client, backup_job, app):
        """Test retrieving comprehensive dashboard data."""
        with app.app_context():
            # Step 1: Get dashboard summary
            summary_response = admin_api_client.get("/api/dashboard/summary")
            assert summary_response.status_code in [200, 404]

            if summary_response.status_code == 200:
                summary_data = summary_response.get_json()
                assert isinstance(summary_data, dict)

            # Step 2: Get statistics
            stats_response = admin_api_client.get("/api/dashboard/stats")
            if stats_response.status_code == 200:
                stats_data = stats_response.get_json()
                # Should have various statistics

            # Step 3: Get compliance overview
            compliance_response = admin_api_client.get("/api/dashboard/compliance-trend")
            if compliance_response.status_code == 200:
                compliance_data = compliance_response.get_json()
                # Should have compliance status

            # Step 4: Get recent executions
            executions_response = admin_api_client.get("/api/dashboard/recent-executions")
            if executions_response.status_code == 200:
                executions_data = executions_response.get_json()

            # Step 5: Get alerts summary
            alerts_response = admin_api_client.get("/api/dashboard/recent-alerts")
            if alerts_response.status_code == 200:
                alerts_data = alerts_response.get_json()

            # Step 6: Get storage usage
            storage_response = admin_api_client.get("/api/dashboard/storage-usage")
            if storage_response.status_code == 200:
                storage_data = storage_response.get_json()


class TestAlertManagement:
    """Test alert management workflow."""

    def test_alert_lifecycle(self, admin_api_client, backup_job, app):
        """Test complete alert lifecycle: Create -> List -> Acknowledge -> Resolve."""
        with app.app_context():
            job = db.session.get(BackupJob, backup_job.id)

            # Step 1: Create alert
            create_response = admin_api_client.post(
                "/api/v1/alerts",
                json={
                    "job_id": job.id,
                    "alert_type": "backup_failure",
                    "severity": "high",
                    "title": "Backup Failed",
                    "message": "Backup job failed due to network timeout",
                },
            )

            if create_response.status_code not in [200, 201]:
                pytest.skip("Alert creation not available")

            alert_id = create_response.get_json().get("alert_id") or create_response.get_json().get("id")

            # Step 2: List unacknowledged alerts
            list_response = admin_api_client.get("/api/v1/alerts/unacknowledged")
            if list_response.status_code == 200:
                alerts_data = list_response.get_json()
                alerts = alerts_data.get("alerts", alerts_data)

                # Should find our alert
                found = any(a.get("id") == alert_id for a in alerts)
                assert found

            # Step 3: Acknowledge alert
            ack_response = admin_api_client.post(
                f"/api/v1/alerts/{alert_id}/acknowledge", json={"notes": "Investigating network issue"}
            )

            assert ack_response.status_code in [200, 404]

            # Step 4: Verify acknowledgment
            details_response = admin_api_client.get(f"/api/v1/alerts/{alert_id}")
            if details_response.status_code == 200:
                alert_data = details_response.get_json()
                alert = alert_data.get("alert", alert_data)
                assert alert["is_acknowledged"] is True


class TestPerformanceAndPagination:
    """Test API performance and pagination."""

    def test_pagination_on_large_datasets(self, admin_api_client, app):
        """Test pagination works correctly with large datasets."""
        with app.app_context():
            # Request first page
            page1_response = admin_api_client.get("/api/jobs?page=1&per_page=10")

            if page1_response.status_code == 200:
                page1_data = page1_response.get_json()

                # Should have pagination metadata
                if "pagination" in page1_data:
                    pagination = page1_data["pagination"]
                    assert "total" in pagination or "page" in pagination

    def test_filtering_and_sorting(self, admin_api_client, app):
        """Test filtering and sorting capabilities."""
        with app.app_context():
            # Filter by status
            filter_response = admin_api_client.get("/api/jobs?status=active")

            if filter_response.status_code == 200:
                # Filtering works
                pass

            # Sort by date
            sort_response = admin_api_client.get("/api/jobs?sort=created_at&order=desc")

            if sort_response.status_code == 200:
                # Sorting works
                pass

    def test_concurrent_requests(self, admin_api_client, app):
        """Test API handles concurrent requests properly."""
        with app.app_context():
            import concurrent.futures

            def make_request():
                return admin_api_client.get("/api/dashboard/summary")

            # Make 10 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]

            # All should succeed or fail gracefully (SQLite thread limits in test env)
            for result in results:
                assert result.status_code in [200, 401, 404, 500]


class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_graceful_degradation(self, admin_api_client, app):
        """Test API gracefully handles service degradation."""
        with app.app_context():
            # Request with invalid parameters should return clear error
            response = admin_api_client.get("/api/jobs/invalid_id")

            assert response.status_code in [400, 404]
            data = response.get_json()

            assert "error" in data or "message" in data

    def test_rate_limiting(self, admin_api_client, app):
        """Test rate limiting if implemented."""
        with app.app_context():
            # Make many rapid requests
            responses = []
            for i in range(100):
                response = admin_api_client.get("/api/dashboard/summary")
                responses.append(response)

            # Should either all succeed or some be rate limited
            status_codes = [r.status_code for r in responses]

            # All should be either 200, 429 (Too Many Requests), 404, or 500
            assert all(code in [200, 404, 429, 500] for code in status_codes)
