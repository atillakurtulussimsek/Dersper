"""Veri modeli.

Tek kurumlu kurulum: `Institution` tablosunda tek satır bulunur.
"""
from __future__ import annotations

import enum
from datetime import datetime, time

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, Time,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class InstitutionType(str, enum.Enum):
    K12 = "k12"
    KURS = "kurs"


class Availability(str, enum.Enum):
    """Bir öğretmenin ya da şubenin bir ders saatindeki durumu."""
    UYGUN = "uygun"
    UYGUN_DEGIL = "uygun_degil"
    TERCIH = "tercih"          # yerleşebilir, tercih edilir


class TimetableStatus(str, enum.Enum):
    TASLAK = "taslak"
    URETILDI = "uretildi"
    YAYINDA = "yayinda"


class SolveStatus(str, enum.Enum):
    BEKLIYOR = "bekliyor"
    CALISIYOR = "calisiyor"
    BASARILI = "basarili"
    COZUMSUZ = "cozumsuz"      # kısıtlar çelişiyor
    HATA = "hata"


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[InstitutionType] = mapped_column(
        Enum(InstitutionType), default=InstitutionType.K12
    )
    address: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Day(Base):
    """Haftanın çalışılan günleri. Ders saati sayısı güne göre değişebilir."""
    __tablename__ = "days"

    id: Mapped[int] = mapped_column(primary_key=True)
    index: Mapped[int] = mapped_column(Integer, unique=True)   # 0 = Pazartesi
    name: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    periods: Mapped[list[Period]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="Period.index"
    )


class Period(Base):
    """Bir gündeki tek bir ders saati (veya teneffüs)."""
    __tablename__ = "periods"
    __table_args__ = (UniqueConstraint("day_id", "index", name="uq_period_day_index"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id", ondelete="CASCADE"))
    index: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(40))
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)

    day: Mapped[Day] = relationship(back_populates="periods")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    short_code: Mapped[str | None] = mapped_column(String(20))
    branch: Mapped[str | None] = mapped_column(String(100))
    max_daily_hours: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    availability: Mapped[list[TeacherAvailability]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )


class TeacherAvailability(Base):
    """Öğretmen müsaitlik matrisi. Kayıt yoksa 'uygun' sayılır."""
    __tablename__ = "teacher_availability"
    __table_args__ = (
        UniqueConstraint("teacher_id", "period_id", name="uq_availability"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id", ondelete="CASCADE"))
    state: Mapped[Availability] = mapped_column(
        Enum(Availability), default=Availability.UYGUN
    )

    teacher: Mapped[Teacher] = relationship(back_populates="availability")


class SectionAvailability(Base):
    """Şube müsaitlik matrisi. Kayıt yoksa 'uygun' sayılır.

    Bazı şubeler yalnızca sabah, bazıları yalnızca akşam ders görür; kapalı
    saatlere o şubenin hiçbir dersi yerleştirilmez.
    """
    __tablename__ = "section_availability"
    __table_args__ = (
        UniqueConstraint("section_id", "period_id", name="uq_section_availability"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"))
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id", ondelete="CASCADE"))
    state: Mapped[Availability] = mapped_column(
        Enum(Availability), default=Availability.UYGUN
    )

    section: Mapped["Section"] = relationship(back_populates="availability")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    short_code: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(7), default="#94a3b8")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Section(Base):
    """Şube — örn. 5-A."""
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    grade_level: Mapped[int | None] = mapped_column(Integer)
    student_count: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    curriculum: Mapped[list[CurriculumEntry]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
    availability: Mapped[list[SectionAvailability]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


class CurriculumEntry(Base):
    """Bir şubede, bir dersin, bir öğretmenle haftalık yükü."""
    __tablename__ = "curriculum_entries"
    __table_args__ = (
        UniqueConstraint("section_id", "subject_id", name="uq_curriculum_section_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"))
    weekly_hours: Mapped[int] = mapped_column(Integer)
    block_size: Mapped[int] = mapped_column(Integer, default=1)   # 2 = çift ders
    max_per_day: Mapped[int] = mapped_column(Integer, default=2)

    section: Mapped[Section] = relationship(back_populates="curriculum")
    subject: Mapped[Subject] = relationship()
    teacher: Mapped[Teacher] = relationship()


class Timetable(Base):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    status: Mapped[TimetableStatus] = mapped_column(
        Enum(TimetableStatus), default=TimetableStatus.TASLAK
    )
    public_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="timetable", cascade="all, delete-orphan"
    )


class Assignment(Base):
    """Yerleşmiş tek bir ders saati."""
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id", ondelete="CASCADE"))
    curriculum_entry_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_entries.id", ondelete="CASCADE")
    )
    period_id: Mapped[int] = mapped_column(ForeignKey("periods.id", ondelete="CASCADE"))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    timetable: Mapped[Timetable] = relationship(back_populates="assignments")
    entry: Mapped[CurriculumEntry] = relationship()
    period: Mapped[Period] = relationship()


class SolveRun(Base):
    """Bir program üretim denemesinin kaydı ve çözümsüzlük raporu."""
    __tablename__ = "solve_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id", ondelete="CASCADE"))
    status: Mapped[SolveStatus] = mapped_column(Enum(SolveStatus), default=SolveStatus.BEKLIYOR)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    seconds: Mapped[float | None] = mapped_column()
    report: Mapped[dict | None] = mapped_column(JSON)        # yapılandırılmış tanı
    ai_explanation: Mapped[str | None] = mapped_column(Text)  # sade Türkçe açıklama


class AiSettings(Base):
    """Kurumun kendi yapay zeka sağlayıcısı. Tek satır."""
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    base_url: Mapped[str | None] = mapped_column(String(300))
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(120), default="gpt-4o-mini")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())
