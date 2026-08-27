"""Başlangıç şeması (v1).

Bu revizyon elle yazılmıştır ve DEĞİŞMEZ. Model tanımlarından üretilseydi,
sonradan eklenen her tablo ve sütun bu revizyona da sızar ve kendi
revizyonuyla çakışırdı. Şema değişiklikleri yeni revizyonlara yazılır.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

KURUM_TIPI = sa.Enum("K12", "KURS", name="institutiontype")
MUSAITLIK = sa.Enum("UYGUN", "UYGUN_DEGIL", "TERCIH", name="availability")
PROGRAM_DURUMU = sa.Enum("TASLAK", "URETILDI", "YAYINDA", name="timetablestatus")
DENEME_DURUMU = sa.Enum(
    "BEKLIYOR", "CALISIYOR", "BASARILI", "COZUMSUZ", "HATA", name="solvestatus"
)


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", KURUM_TIPI, nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
    )
    # Model e-postayı hem unique hem index olarak tanımlar; SQLAlchemy bunu
    # tek bir benzersiz indeksle karşılar.
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("index", name="uq_days_index"),
    )

    op.create_table(
        "periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day_id", sa.Integer(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("is_break", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["day_id"], ["days.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("day_id", "index", name="uq_period_day_index"),
    )

    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("short_code", sa.String(20), nullable=True),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("max_daily_hours", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "teacher_availability",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("state", MUSAITLIK, nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["period_id"], ["periods.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("teacher_id", "period_id", name="uq_availability"),
    )

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("short_code", sa.String(20), nullable=True),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=True),
        sa.Column("student_count", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("name", name="uq_sections_name"),
    )

    op.create_table(
        "curriculum_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("weekly_hours", sa.Integer(), nullable=False),
        sa.Column("block_size", sa.Integer(), nullable=False),
        sa.Column("max_per_day", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("section_id", "subject_id",
                            name="uq_curriculum_section_subject"),
    )

    op.create_table(
        "timetables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("status", PROGRAM_DURUMU, nullable=False),
        sa.Column("public_token", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.UniqueConstraint("public_token", name="uq_timetables_public_token"),
    )

    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timetable_id", sa.Integer(), nullable=False),
        sa.Column("curriculum_entry_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["timetable_id"], ["timetables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["curriculum_entry_id"], ["curriculum_entries.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["period_id"], ["periods.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "solve_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("timetable_id", sa.Integer(), nullable=False),
        sa.Column("status", DENEME_DURUMU, nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("seconds", sa.Float(), nullable=True),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["timetable_id"], ["timetables.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("base_url", sa.String(300), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    for tablo in (
        "ai_settings", "solve_runs", "assignments", "timetables",
        "curriculum_entries", "sections", "subjects", "teacher_availability",
        "teachers", "periods", "days", "users", "institutions",
    ):
        op.drop_table(tablo)
