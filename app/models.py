"""
Database models for Backup Management System
Implements 3-2-1-1-0 backup rule compliance tracking

Tables:
- users: User management
- backup_jobs: Backup job definitions
- backup_copies: Backup copy information (primary/secondary/offsite/offline)
- offline_media: Offline media inventory (tapes, external HDDs)
- media_rotation_schedule: Media rotation scheduling
- media_lending: Media lending records
- verification_tests: Verification test execution records
- verification_schedule: Verification test scheduling
- backup_executions: Backup execution history
- compliance_status: 3-2-1-1-0 rule compliance status cache
- alerts: Alert management
- audit_logs: Audit log records
- reports: Generated report metadata
- system_settings: System configuration key-value store
"""

from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User model with role-based access control
    Roles: admin, operator, viewer, auditor
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    department = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False, index=True)  # admin/operator/viewer/auditor
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime)

    # Login attempt tracking
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_failed_login = db.Column(db.DateTime)
    account_locked_until = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    backup_jobs = db.relationship("BackupJob", back_populates="owner", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")
    owned_media = db.relationship("OfflineMedia", back_populates="owner", lazy="dynamic")
    verified_tests = db.relationship("VerificationTest", back_populates="tester", lazy="dynamic")
    borrowed_media = db.relationship("MediaLending", back_populates="borrower", lazy="dynamic")
    generated_reports = db.relationship("Report", back_populates="generator", lazy="dynamic")
    acknowledged_alerts = db.relationship("Alert", back_populates="acknowledger", lazy="dynamic")
    updated_settings = db.relationship("SystemSetting", back_populates="updater", lazy="dynamic")
    assigned_verifications = db.relationship("VerificationSchedule", back_populates="assignee", lazy="dynamic")

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user is admin"""
        return self.role == "admin"

    def is_operator(self):
        """Check if user is operator or above"""
        return self.role in ("admin", "operator")

    def is_auditor(self):
        """Check if user is auditor"""
        return self.role == "auditor"

    def can_edit(self):
        """Check if user can edit data"""
        return self.role in ("admin", "operator")

    def can_view(self):
        """Check if user can view data"""
        return self.is_active and self.role in ("admin", "operator", "viewer", "auditor")

    def has_any_role(self, *roles):
        """Check if user has any of the specified roles"""
        return self.role in roles

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class BackupJob(db.Model):
    """
    Backup job definition
    Types: system_image, file, database, vm
    Tools: veeam, wsb, aomei, custom
    """

    __tablename__ = "backup_jobs"

    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(100), nullable=False, index=True)
    job_type = db.Column(db.String(50), nullable=False, index=True)  # system_image/file/database/vm
    target_server = db.Column(db.String(100))
    target_path = db.Column(db.String(500))
    backup_tool = db.Column(db.String(50), nullable=False)  # veeam/wsb/aomei/custom
    schedule_type = db.Column(db.String(20), nullable=False)  # daily/weekly/monthly/manual
    retention_days = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = db.relationship("User", back_populates="backup_jobs")
    copies = db.relationship("BackupCopy", back_populates="job", cascade="all, delete-orphan", lazy="dynamic")
    executions = db.relationship("BackupExecution", back_populates="job", cascade="all, delete-orphan", lazy="dynamic")
    verification_tests = db.relationship(
        "VerificationTest", back_populates="job", cascade="all, delete-orphan", lazy="dynamic"
    )
    verification_schedules = db.relationship(
        "VerificationSchedule", back_populates="job", cascade="all, delete-orphan", lazy="dynamic"
    )
    compliance_statuses = db.relationship(
        "ComplianceStatus", back_populates="job", cascade="all, delete-orphan", lazy="dynamic"
    )
    alerts = db.relationship("Alert", back_populates="job", lazy="dynamic")

    notification_logs = db.relationship("NotificationLog", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BackupJob {self.job_name} ({self.job_type})>"


class BackupCopy(db.Model):
    """
    Backup copy information
    Copy types: primary, secondary, offsite, offline
    Media types: disk, tape, cloud, external_hdd
    """

    __tablename__ = "backup_copies"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("backup_jobs.id"), nullable=False, index=True)
    copy_type = db.Column(db.String(20), nullable=False, index=True)  # primary/secondary/offsite/offline
    media_type = db.Column(db.String(20), nullable=False, index=True)  # disk/tape/cloud/external_hdd
    storage_path = db.Column(db.String(500))
    is_encrypted = db.Column(db.Boolean, default=False, nullable=False)
    is_compressed = db.Column(db.Boolean, default=False, nullable=False)
    last_backup_date = db.Column(db.DateTime)
    last_backup_size = db.Column(db.BigInteger)  # bytes
    status = db.Column(db.String(20), default="unknown", nullable=False)  # success/failed/warning/unknown
    offline_media_id = db.Column(db.Integer, db.ForeignKey("offline_media.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    job = db.relationship("BackupJob", back_populates="copies")
    offline_media = db.relationship("OfflineMedia", back_populates="backup_copies")

    def __repr__(self):
        return f"<BackupCopy job_id={self.job_id} type={self.copy_type} media={self.media_type}>"


class OfflineMedia(db.Model):
    """
    Offline media inventory (tapes, external HDDs, USB drives)
    Status: in_use, stored, retired
    """

    __tablename__ = "offline_media"

    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # Barcode or label
    media_type = db.Column(db.String(20), nullable=False, index=True)  # external_hdd/tape/usb
    capacity_gb = db.Column(db.Integer)
    purchase_date = db.Column(db.Date)
    storage_location = db.Column(db.String(200))
    current_status = db.Column(db.String(20), default="available", nullable=False, index=True)  # in_use/stored/retired
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    qr_code = db.Column(db.Text)  # Base64 encoded QR code image
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner = db.relationship("User", back_populates="owned_media")
    backup_copies = db.relationship("BackupCopy", back_populates="offline_media", lazy="dynamic")
    rotation_schedules = db.relationship(
        "MediaRotationSchedule", back_populates="media", cascade="all, delete-orphan", lazy="dynamic"
    )
    lending_records = db.relationship("MediaLending", back_populates="media", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<OfflineMedia {self.media_id} ({self.media_type})>"


class MediaRotationSchedule(db.Model):
    """
    Media rotation schedule
    Rotation types: gfs (Grandfather-Father-Son), tower_of_hanoi, custom
    """

    __tablename__ = "media_rotation_schedule"

    id = db.Column(db.Integer, primary_key=True)
    offline_media_id = db.Column(db.Integer, db.ForeignKey("offline_media.id"), nullable=False, index=True)
    rotation_type = db.Column(db.String(20), nullable=False)  # gfs/tower_of_hanoi/custom
    rotation_cycle = db.Column(db.String(20), nullable=False)  # weekly/monthly
    next_rotation_date = db.Column(db.Date, nullable=False, index=True)
    last_rotation_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    media = db.relationship("OfflineMedia", back_populates="rotation_schedules")

    def __repr__(self):
        return f"<MediaRotationSchedule media_id={self.offline_media_id} type={self.rotation_type}>"


class MediaLending(db.Model):
    """
    Media lending records
    Tracks borrowing and return of offline media
    """

    __tablename__ = "media_lending"

    id = db.Column(db.Integer, primary_key=True)
    offline_media_id = db.Column(db.Integer, db.ForeignKey("offline_media.id"), nullable=False, index=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    borrow_purpose = db.Column(db.String(200))
    borrow_date = db.Column(db.DateTime, nullable=False)
    expected_return = db.Column(db.Date, nullable=False)
    actual_return = db.Column(db.DateTime, index=True)  # NULL = still borrowed
    return_condition = db.Column(db.String(20))  # normal/abnormal
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    media = db.relationship("OfflineMedia", back_populates="lending_records")
    borrower = db.relationship("User", back_populates="borrowed_media")

    def __repr__(self):
        return f"<MediaLending media_id={self.offline_media_id} borrower={self.borrower_id}>"


class VerificationTest(db.Model):
    """
    Verification test execution records
    Test types: full_restore, partial, integrity
    """

    __tablename__ = "verification_tests"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("backup_jobs.id"), nullable=False, index=True)
    test_type = db.Column(db.String(50), nullable=False)  # full_restore/partial/integrity
    test_date = db.Column(db.DateTime, nullable=False, index=True)
    tester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    restore_target = db.Column(db.String(200))
    test_result = db.Column(db.String(20), nullable=False, index=True)  # success/failed
    duration_seconds = db.Column(db.Integer)
    issues_found = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    job = db.relationship("BackupJob", back_populates="verification_tests")
    tester = db.relationship("User", back_populates="verified_tests")

    def __repr__(self):
        return f"<VerificationTest job_id={self.job_id} type={self.test_type} result={self.test_result}>"


class VerificationSchedule(db.Model):
    """
    Verification test schedule
    Frequencies: monthly, quarterly, semi-annual, annual
    """

    __tablename__ = "verification_schedule"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("backup_jobs.id"), nullable=False, index=True)
    test_frequency = db.Column(db.String(20), nullable=False)  # monthly/quarterly/semi-annual/annual
    next_test_date = db.Column(db.Date, nullable=False, index=True)
    last_test_date = db.Column(db.Date)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    job = db.relationship("BackupJob", back_populates="verification_schedules")
    assignee = db.relationship("User", back_populates="assigned_verifications")

    def __repr__(self):
        return f"<VerificationSchedule job_id={self.job_id} frequency={self.test_frequency}>"


class BackupExecution(db.Model):
    """
    Backup execution history
    Results: success, failed, warning
    """

    __tablename__ = "backup_executions"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("backup_jobs.id"), nullable=False, index=True)
    execution_date = db.Column(db.DateTime, nullable=False, index=True)
    execution_result = db.Column(db.String(20), nullable=False, index=True)  # success/failed/warning
    error_message = db.Column(db.Text)
    backup_size_bytes = db.Column(db.BigInteger)
    duration_seconds = db.Column(db.Integer)
    source_system = db.Column(db.String(100))  # powershell/manual/scheduled
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = db.relationship("BackupJob", back_populates="executions")

    def __repr__(self):
        return f"<BackupExecution job_id={self.job_id} result={self.execution_result} date={self.execution_date}>"


class ComplianceStatus(db.Model):
    """3-2-1-1-0 rule compliance status cache"""

    __tablename__ = "compliance_status"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("backup_jobs.id"), nullable=False, index=True)
    check_date = db.Column(db.DateTime, nullable=False, index=True)
    copies_count = db.Column(db.Integer, nullable=False)
    media_types_count = db.Column(db.Integer, nullable=False)
    has_offsite = db.Column(db.Boolean, nullable=False)
    has_offline = db.Column(db.Boolean, nullable=False)
    has_errors = db.Column(db.Boolean, nullable=False)
    overall_status = db.Column(db.String(20), nullable=False, index=True)  # compliant, non_compliant, warning
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = db.relationship("BackupJob", back_populates="compliance_statuses")

    def __repr__(self):
        return f"<ComplianceStatus job_id={self.job_id} status={self.overall_status}>"


class Alert(db.Model):
    """
    Alert management
    Types: backup_failed, rule_violation, verification_overdue, media_error, etc.
    Severity: info, warning, error, critical
    """

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, index=True)  # info/warning/error/critical
    job_id = db.Column(db.Integer, db.ForeignKey("backup_jobs.id"))
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_acknowledged = db.Column(db.Boolean, default=False, nullable=False, index=True)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    acknowledged_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    job = db.relationship("BackupJob", back_populates="alerts")
    acknowledger = db.relationship("User", back_populates="acknowledged_alerts")
    notification_logs = db.relationship("NotificationLog", back_populates="alert", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Alert {self.alert_type} severity={self.severity} ack={self.is_acknowledged}>"


class AuditLog(db.Model):
    """
    Audit log for security and compliance
    Tracks all user actions
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)  # login/create/update/delete/export
    resource_type = db.Column(db.String(50))  # user/job/media/report
    resource_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))  # IPv4/IPv6
    action_result = db.Column(db.String(20), nullable=False)  # success/failed
    details = db.Column(db.Text)  # JSON format
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog user_id={self.user_id} action={self.action_type} result={self.action_result}>"


class Report(db.Model):
    """
    Generated report metadata
    Types: daily, weekly, monthly, compliance, audit
    Formats: html, pdf, csv
    """

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(50), nullable=False, index=True)  # daily/weekly/monthly/compliance/audit
    report_title = db.Column(db.String(200), nullable=False)
    date_from = db.Column(db.Date, nullable=False)
    date_to = db.Column(db.Date, nullable=False)
    file_path = db.Column(db.String(500))
    file_format = db.Column(db.String(10), nullable=False)  # html/pdf/csv
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    generator = db.relationship("User", back_populates="generated_reports")

    notification_logs = db.relationship("NotificationLog", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Report {self.report_type} from={self.date_from} to={self.date_to}>"


class SystemSetting(db.Model):
    """
    System configuration key-value store
    Value types: string, int, bool, json
    """

    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.Text)
    value_type = db.Column(db.String(20), nullable=False)  # string/int/bool/json
    description = db.Column(db.Text)
    is_encrypted = db.Column(db.Boolean, default=False, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    updater = db.relationship("User", back_populates="updated_settings")

    def __repr__(self):
        return f"<SystemSetting {self.setting_key}={self.setting_value}>"


class NotificationLog(db.Model):
    """
    Notification delivery history and tracking
    Records all notification attempts (Email, Teams, Dashboard)
    """

    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(50), nullable=False, index=True)  # email/teams/dashboard
    channel = db.Column(db.String(50), nullable=False)  # specific channel name
    recipient = db.Column(db.String(255), nullable=False)  # email address or teams webhook
    subject = db.Column(db.String(500))
    message = db.Column(db.Text)
    severity = db.Column(db.String(20), index=True)  # info/warning/error/critical
    status = db.Column(db.String(20), nullable=False, index=True)  # sent/failed/pending
    error_message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Related entities
    alert_id = db.Column(db.Integer, db.ForeignKey("alerts.id"))
    job_id = db.Column(db.Integer, db.ForeignKey("backup_jobs.id"))
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id"))

    # Metadata
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    delivery_time_ms = db.Column(db.Integer)  # Time taken to deliver

    # Relationships
    alert = db.relationship("Alert", back_populates="notification_logs")
    job = db.relationship("BackupJob", back_populates="notification_logs")
    report = db.relationship("Report", back_populates="notification_logs")

    def __repr__(self):
        return f"<NotificationLog {self.notification_type} to {self.recipient} - {self.status}>"
