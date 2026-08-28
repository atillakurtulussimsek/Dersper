"""İstek/yanıt şemaları."""
from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app import bloklar
from app.models import Availability, InstitutionType, SolveStatus, TimetableStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Dönem ---

class TermIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    starts_on: date | None = None
    ends_on: date | None = None


class TermOut(ORMModel):
    id: int
    name: str
    starts_on: date | None
    ends_on: date | None
    created_at: datetime
    is_active: bool = False
    # Dönemde tanımlı kayıt sayıları — listede özet göstermek için.
    counts: dict[str, int] = {}


class ImportIn(BaseModel):
    """Geçmiş dönemden seçili kayıtları aktif döneme aktarır."""
    term_id: int
    ids: list[int] = Field(min_length=1)


class ImportOut(BaseModel):
    imported: int
    skipped: list[str]


# --- Kurulum & oturum ---

class SetupRequest(BaseModel):
    institution_name: str = Field(min_length=2, max_length=200)
    institution_type: InstitutionType = InstitutionType.K12
    term_name: str = Field(default="2026-2027 Güz Dönemi", min_length=1, max_length=150)
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SetupStatus(BaseModel):
    completed: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    is_active: bool


class InstitutionOut(ORMModel):
    id: int
    name: str
    type: InstitutionType
    address: str | None


class InstitutionUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    type: InstitutionType
    address: str | None = None


# --- Zaman ızgarası ---

class PeriodIn(BaseModel):
    index: int
    name: str = Field(max_length=40)
    start_time: time | None = None
    end_time: time | None = None
    is_break: bool = False


class PeriodOut(ORMModel):
    id: int
    day_id: int
    index: int
    name: str
    start_time: time | None
    end_time: time | None
    is_break: bool


class DayIn(BaseModel):
    index: int
    name: str = Field(max_length=20)
    is_active: bool = True
    periods: list[PeriodIn] = []


class DayOut(ORMModel):
    id: int
    index: int
    name: str
    is_active: bool
    periods: list[PeriodOut]


# --- Öğretmen ---

class TeacherIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    short_code: str | None = Field(default=None, max_length=20)
    branch: str | None = Field(default=None, max_length=100)
    max_daily_hours: int | None = Field(default=None, ge=1, le=20)
    notes: str | None = None
    color: str = Field(default="#94a3b8", pattern=r"^#[0-9a-fA-F]{6}$")
    is_active: bool = True


class TeacherOut(ORMModel):
    id: int
    full_name: str
    short_code: str | None
    branch: str | None
    max_daily_hours: int | None
    notes: str | None
    color: str
    is_active: bool


class AvailabilityCell(BaseModel):
    period_id: int
    state: Availability


class AvailabilityUpdate(BaseModel):
    cells: list[AvailabilityCell]


class AvailabilityCopyIn(BaseModel):
    """Bir şubenin müsaitlik tablosunu başka şubelere kopyalar."""
    section_ids: list[int] = Field(min_length=1)


class AvailabilityCopyOut(BaseModel):
    # Kopyalanan şube adları
    copied_to: list[str]
    # Her hedefe yazılan işaretli hücre sayısı
    cells: int


# --- Ders & şube ---

class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    short_code: str | None = Field(default=None, max_length=20)
    color: str = Field(default="#94a3b8", pattern=r"^#[0-9a-fA-F]{6}$")
    is_active: bool = True


class SubjectOut(ORMModel):
    id: int
    name: str
    short_code: str | None
    color: str
    is_active: bool


class SectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    grade_level: int | None = Field(default=None, ge=1, le=13)
    student_count: int | None = Field(default=None, ge=0, le=200)
    is_active: bool = True


class SectionOut(ORMModel):
    id: int
    name: str
    grade_level: int | None
    student_count: int | None
    is_active: bool


class CurriculumIn(BaseModel):
    section_id: int
    subject_id: int
    teacher_id: int
    weekly_hours: int = Field(ge=1, le=40)
    # Haftalık saatin gün içindeki parçalanışı, örn. "2+2+1".
    # Boş bırakılırsa saatler tek tek dağıtılır.
    block_pattern: str = Field(default="", max_length=60)
    max_per_day: int = Field(default=2, ge=1, le=10)

    @model_validator(mode="after")
    def _deseni_dogrula(self) -> "CurriculumIn":
        try:
            self.block_pattern = bloklar.duzenle(self.block_pattern, self.weekly_hours)
        except bloklar.DesenHatasi as e:
            raise ValueError(str(e)) from e
        return self


class CurriculumCopyIn(BaseModel):
    """Seçili müfredat satırlarını başka şubelere kopyalar."""
    entry_ids: list[int] = Field(min_length=1)
    section_ids: list[int] = Field(min_length=1)


class CurriculumOut(ORMModel):
    id: int
    section_id: int
    subject_id: int
    teacher_id: int
    weekly_hours: int
    block_pattern: str
    max_per_day: int
    subject: SubjectOut
    teacher: TeacherOut
    section: SectionOut


class CurriculumCopyOut(BaseModel):
    created: list[CurriculumOut]
    # Kopyalanamayanlar için kullanıcıya gösterilecek gerekçeler.
    skipped: list[str]


# --- Program ---

class TimetableIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class TimetableOut(ORMModel):
    id: int
    name: str
    status: TimetableStatus
    public_token: str | None
    created_at: datetime


class AssignmentOut(ORMModel):
    id: int
    curriculum_entry_id: int
    period_id: int
    is_locked: bool


class AssignmentMove(BaseModel):
    period_id: int


class GridCell(BaseModel):
    """Arayüzün ızgarada gösterdiği hazır hücre."""
    assignment_id: int
    period_id: int
    day_index: int
    period_index: int
    section_id: int
    section_name: str
    subject_name: str
    subject_short: str | None
    subject_color: str
    teacher_id: int
    teacher_name: str
    teacher_short: str | None
    is_locked: bool


class TimetableGrid(BaseModel):
    timetable: TimetableOut
    cells: list[GridCell]


class SolveRunOut(ORMModel):
    id: int
    timetable_id: int
    status: SolveStatus
    started_at: datetime
    finished_at: datetime | None
    seconds: float | None
    report: dict | None
    ai_explanation: str | None


# --- Yapay zeka ayarları ---

class AiSettingsIn(BaseModel):
    enabled: bool = False
    base_url: str | None = None
    api_key: str | None = None      # boş bırakılırsa kayıtlı anahtar korunur
    model: str = "gpt-4o-mini"


class AiSettingsOut(BaseModel):
    enabled: bool
    base_url: str | None
    model: str
    api_key_masked: str
    has_api_key: bool


class AiTestResult(BaseModel):
    ok: bool
    message: str
