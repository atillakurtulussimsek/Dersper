"""Veri modeli.

Tek kurumlu kurulum: `Institution` tablosunda tek satır bulunur.

Tüm tanımlar bir **döneme** (`Term`) aittir: zaman ızgarası, öğretmenler,
dersler, şubeler, müfredat ve programlar. Yeni dönem boş başlar; geçmiş
dönemden kayıt aktarmak isteğe bağlıdır. Hangi dönemde çalışıldığı sunucuda,
`Institution.active_term_id` alanında tutulur.

Silme her yerde **yumuşaktır**: kayıt `deleted_at` ile işaretlenir, veritabanından
hiçbir zaman kaldırılmaz.
"""
from __future__ import annotations

import enum
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text,
    Time, UniqueConstraint, func,
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


class SoftDelete:
    """Yumuşak silme. `deleted_at` doluysa kayıt listelerde görünmez."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[InstitutionType] = mapped_column(
        Enum(InstitutionType), default=InstitutionType.K12
    )
    address: Mapped[str | None] = mapped_column(String(500))
    # Üzerinde çalışılan dönem. Tüm uçlar bu döneme göre süzer.
    active_term_id: Mapped[int | None] = mapped_column(
        ForeignKey("terms.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Term(Base, SoftDelete):
    """Öğretim dönemi. Tüm tanımlar bir döneme bağlıdır."""

    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
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
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    index: Mapped[int] = mapped_column(Integer)                # 0 = Pazartesi
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


class Teacher(Base, SoftDelete):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(200))
    short_code: Mapped[str | None] = mapped_column(String(20))
    branch: Mapped[str | None] = mapped_column(String(100))
    max_daily_hours: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(7), default="#94a3b8")
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


class Subject(Base, SoftDelete):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    short_code: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(7), default="#94a3b8")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Section(Base, SoftDelete):
    """Şube — örn. 5-A."""
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))
    grade_level: Mapped[int | None] = mapped_column(Integer)
    student_count: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    curriculum: Mapped[list[CurriculumEntry]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
    availability: Mapped[list[SectionAvailability]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


class CurriculumEntry(Base, SoftDelete):
    """Bir şubede, bir dersin, bir öğretmenle haftalık yükü.

    Şube–ders eşsizliği uygulama katmanında, silinmemiş satırlar üzerinde
    denetlenir; veritabanı kısıtı yumuşak silmeyle bağdaşmaz.
    """
    __tablename__ = "curriculum_entries"
    # Kaldırılan benzersiz kısıtın yerine: section_id yabancı anahtarı indeks ister.
    __table_args__ = (Index("ix_curriculum_section", "section_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"))
    weekly_hours: Mapped[int] = mapped_column(Integer)
    # Haftalık saatin gün içindeki parçalanışı, örn. "2+2+1". Toplamı weekly_hours eder.
    block_pattern: Mapped[str] = mapped_column(String(60), default="")
    max_per_day: Mapped[int] = mapped_column(Integer, default=2)

    section: Mapped[Section] = relationship(back_populates="curriculum")
    subject: Mapped[Subject] = relationship()
    teacher: Mapped[Teacher] = relationship()


class Timetable(Base, SoftDelete):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
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
