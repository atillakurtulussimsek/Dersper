"""İstek/yanıt şemaları."""
from __future__ import annotations

from datetime import date, datetime, time

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app import bloklar
from app.models import (
    Availability, ConflictBasis, GapPolicy, InstitutionType, SectionOrder,
    SolveStatus, TimetableStatus, VersionKind,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Dönem ---

class TermIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    starts_on: date | None = None
    ends_on: date | None = None
    # Açıkken bir öğretmen bir günde tek binada ders verir.
    block_building_switch: bool = False
    # Çakışma neye göre ölçülür: ızgaranın satırı mı, gerçek saat aralığı mı?
    conflict_basis: ConflictBasis = ConflictBasis.DERS_SAATI
    # Şubeler ada göre mi, elle verilen sırayla mı dizilir?
    section_order: SectionOrder = SectionOrder.AD


class TermOut(ORMModel):
    id: int
    name: str
    starts_on: date | None
    ends_on: date | None
    block_building_switch: bool = False
    conflict_basis: ConflictBasis = ConflictBasis.DERS_SAATI
    section_order: SectionOrder = SectionOrder.AD
    created_at: datetime
    is_active: bool = False
    # Dönemde tanımlı kayıt sayıları — listede özet göstermek için.
    counts: dict[str, int] = {}


class SectionOrderIn(BaseModel):
    """Şubelerin elle sırası: kimlikler, istenen sırayla."""
    ids: list[int] = Field(min_length=1)


class TermCopyIn(BaseModel):
    """Dönemin tamamının kopyası: yeni ad ve isteğe bağlı tarihler."""
    name: str = Field(min_length=1, max_length=150)
    starts_on: date | None = None
    ends_on: date | None = None
    # Kopya hemen çalışılan dönem olsun mu?
    activate: bool = True


class TermCopyOut(BaseModel):
    term: "TermOut"
    # Neyin kaç tane kopyalandığı — kullanıcıya özet.
    copied: dict[str, int]


class ImportIn(BaseModel):
    """Geçmiş dönemden seçili kayıtları aktif döneme aktarır."""
    term_id: int
    ids: list[int] = Field(min_length=1)


class ImportOut(BaseModel):
    imported: int
    skipped: list[str]


# --- Kurulum & oturum ---

class RegisterRequest(BaseModel):
    """Yeni kurum kaydı: kurum, ilk kullanıcı ve ilk dönem birlikte açılır."""
    institution_name: str = Field(min_length=2, max_length=200)
    institution_type: InstitutionType = InstitutionType.K12
    term_name: str = Field(default="2026-2027 Güz Dönemi", min_length=1, max_length=150)
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthStatus(BaseModel):
    # Sistemde hiç kurum var mı — yoksa ilk kayıt her durumda açıktır.
    has_institutions: bool
    # Yeni kurum kaydı şu an yapılabilir mi?
    registration_open: bool


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


class UserCreate(BaseModel):
    """Kuruma kullanıcı ekleme. Rol yoktur; herkes yöneticidir."""
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    is_active: bool = True
    # Boş bırakılırsa parola değişmez.
    password: str | None = Field(default=None, min_length=8, max_length=128)


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
    # Var olan bir ders saatinin kimliği. Gönderilirse satır SIRAYA göre değil
    # kimliğe göre eşleştirilir; sıralama değiştiğinde müsaitlik işaretleri
    # taşınan satırın peşinden gider. Yeni satırlarda boş bırakılır.
    id: int | None = None
    index: int
    name: str = Field(max_length=40)
    start_time: time | None = None
    end_time: time | None = None
    is_break: bool = False
    is_lunch: bool = False

    @model_validator(mode="after")
    def _ogle_arasi_teneffustur(self) -> "PeriodIn":
        """Öğle arasına ders konmaz; işaretlendiğinde teneffüs de olur."""
        if self.is_lunch:
            self.is_break = True
        return self


class PeriodOut(ORMModel):
    id: int
    day_id: int
    index: int
    name: str
    start_time: time | None
    end_time: time | None
    is_break: bool
    is_lunch: bool


class DayIn(BaseModel):
    index: int
    name: str = Field(max_length=20)
    is_active: bool = True
    periods: list[PeriodIn] = []

    @model_validator(mode="after")
    def _tek_ogle_arasi(self) -> "DayIn":
        """Gün ikiye bölünür; ikinci bir öğle arası bölmeyi belirsizleştirirdi."""
        if sum(1 for p in self.periods if p.is_lunch) > 1:
            raise ValueError(
                f"{self.name} gününde birden fazla öğle arası var. "
                f"Bir günde yalnızca bir öğle arası olabilir."
            )
        return self

    @model_validator(mode="after")
    def _sira_ve_kimlik_tekil(self) -> "DayIn":
        """Sıra ve kimlik gün içinde tekil olmalı.

        Yinelenen sıra veritabanındaki benzersizlik kısıtına takılır, yinelenen
        kimlik ise aynı satırı iki yere koymaya çalışmak demektir. İkisi de
        veritabanı hatasına düşmeden burada yakalanır.
        """
        siralar = [p.index for p in self.periods]
        if len(set(siralar)) != len(siralar):
            raise ValueError(f"{self.name} gününde aynı sıra numarası birden fazla kez var.")
        kimlikler = [p.id for p in self.periods if p.id is not None]
        if len(set(kimlikler)) != len(kimlikler):
            raise ValueError(f"{self.name} gününde aynı ders saati birden fazla kez gönderildi.")
        return self


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
    # Haftada okulda bulunabileceği en fazla gün. Yarım gün kabul edilir
    # (örn. 4.5); başka kesir yoktur. NULL = sınır yok.
    max_days: float | None = Field(default=None, gt=0, le=7)
    notes: str | None = None
    color: str = Field(default="#94a3b8", pattern=r"^#[0-9a-fA-F]{6}$")
    is_active: bool = True

    @model_validator(mode="after")
    def _yarim_gun_kontrolu(self) -> "TeacherIn":
        """Kesir yalnızca yarım olabilir: yarım gün öğle arasıyla tanımlıdır,
        çeyrek günün ızgarada bir karşılığı yok."""
        if self.max_days is not None and (self.max_days * 2) % 1 != 0:
            raise ValueError(
                "Gün sınırı tam ya da yarım olmalı (örn. 4 veya 4,5). "
                f"{self.max_days} kabul edilmiyor."
            )
        return self

    @property
    def max_half_days(self) -> int | None:
        """Veritabanının sakladığı birim: yarım gün."""
        return None if self.max_days is None else round(self.max_days * 2)


class TeacherOut(ORMModel):
    id: int
    full_name: str
    short_code: str | None
    branch: str | None
    max_daily_hours: int | None
    max_days: float | None
    notes: str | None
    color: str
    is_active: bool


class AvailabilityCell(BaseModel):
    period_id: int
    state: Availability


class AvailabilityUpdate(BaseModel):
    cells: list[AvailabilityCell]


class ClosedAvailabilityOut(BaseModel):
    """Dönemin kapalı saatleri: kayıt kimliği -> ders saati kimlikleri."""
    teachers: dict[int, list[int]]
    sections: dict[int, list[int]]


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


class BuildingIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    short_code: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    is_active: bool = True


class BuildingOut(ORMModel):
    id: int
    name: str
    short_code: str | None
    notes: str | None
    is_active: bool


class SectionIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    grade_level: int | None = Field(default=None, ge=1, le=13)
    student_count: int | None = Field(default=None, ge=0, le=200)
    # Şubenin dersliğinin bulunduğu bina. NULL = tek binalı kurum.
    building_id: int | None = None
    is_active: bool = True


class SectionOut(ORMModel):
    id: int
    name: str
    grade_level: int | None
    student_count: int | None
    building_id: int | None
    is_active: bool
    sort_order: int | None = None


class CurriculumIn(BaseModel):
    section_id: int
    # Birleşik ders: bu satırı `section_id` ile birlikte gören ek şubeler.
    # Beden eğitimi, din kültürü ve seçmeliler sık sık böyle okutulur —
    # tek öğretmen, tek saat, birkaç şube. Boşsa ders tek şubeliktir.
    extra_section_ids: list[int] = []
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
        ek = [x for x in self.extra_section_ids if x != self.section_id]
        if len(set(ek)) != len(ek):
            raise ValueError("Aynı şube birden fazla kez seçilemez.")
        self.extra_section_ids = ek
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
    # Dersi birlikte gören şubeler; asıl şube başta. Tek şubeliyse tek elemanlı.
    sections: list[SectionOut] = []


class CurriculumCopyOut(BaseModel):
    created: list[CurriculumOut]
    # Kopyalanamayanlar için kullanıcıya gösterilecek gerekçeler.
    skipped: list[str]


# --- Program ---

class TimetableIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    # None = dönemin tüm şubeleri.
    section_ids: list[int] | None = None
    gap_policy: GapPolicy = GapPolicy.IDEAL


class TimetableUpdate(BaseModel):
    """Üretim öncesi değiştirilebilen alanlar."""
    name: str | None = Field(default=None, min_length=1, max_length=150)
    gap_policy: GapPolicy | None = None


class TimetableOut(ORMModel):
    id: int
    name: str
    status: TimetableStatus
    public_token: str | None
    section_ids: list[int] | None
    gap_policy: GapPolicy
    created_at: datetime


class AssignmentOut(ORMModel):
    id: int
    curriculum_entry_id: int
    period_id: int
    is_locked: bool


class AssignmentMove(BaseModel):
    period_id: int


class PlaceIn(BaseModel):
    """Bekleyen bir bloğu ızgaraya koyar."""
    curriculum_entry_id: int
    period_id: int
    uzunluk: int = Field(ge=1, le=20)


class TargetOut(BaseModel):
    """Sürüklenen ders için tek bir saatin değerlendirmesi."""
    period_id: int
    uygun: bool
    neden: str | None


class PendingOut(BaseModel):
    """Bekleyenler rafındaki tek bir blok."""
    curriculum_entry_id: int
    uzunluk: int
    section_name: str
    subject_name: str
    subject_color: str
    teacher_name: str


class GridCell(BaseModel):
    """Arayüzün ızgarada gösterdiği hazır hücre."""
    assignment_id: int
    period_id: int
    day_index: int
    period_index: int
    # Asıl şube. Birleşik derste hücre yine tektir; tüm şubeler aşağıdadır.
    section_id: int
    section_name: str
    # Dersi birlikte gören şubeler. Tek şubeliyse tek elemanlı.
    section_ids: list[int] = []
    section_names: list[str] = []
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
    # Dönemin şubeleri, kurumun seçtiği sırayla. Şeritler, çarşaf satırları ve
    # yayın sayfası bu sırayı kullanır — hepsi tek yerden.
    section_names: list[str] = []
    # Geri/ileri alınacak sürüm var mı — arayüz düğmeleri buna göre açılır.
    can_undo: bool = False
    can_redo: bool = False
    # Programın durduğu sürüm numarası.
    version: int | None = None


class VersionOut(ORMModel):
    """Geçmiş listesindeki tek bir sürüm."""
    number: int
    kind: VersionKind
    label: str
    placed: int
    created_at: datetime


class DiffKonum(BaseModel):
    period_id: int
    gun: str
    saat: str
    gun_index: int
    period_index: int


class DiffDegisiklik(BaseModel):
    tur: Literal["tasindi", "cikti", "eklendi", "kilitlendi", "kilit_acildi"]
    entry_id: int
    sube: str
    ders: str
    ogretmen: str
    kaynak: DiffKonum | None
    hedef: DiffKonum | None


class VersionDiffOut(BaseModel):
    """İki sürüm arasındaki fark: A'dan B'ye."""
    a: VersionOut
    b: VersionOut
    # tasindi / cikti / eklendi / kilit sayıları ve etkilenen ders sayısı.
    ozet: dict[str, int]
    degisiklikler: list[DiffDegisiklik]


class WarningOut(BaseModel):
    key: str
    tur: str
    baslik: str
    detay: str
    sube: str
    ders: str
    ogretmen: str
    gun: str
    konan: int
    sinir: int
    ignored: bool


class WarningIgnoreIn(BaseModel):
    key: str


class SolveRunOut(ORMModel):
    id: int
    timetable_id: int
    status: SolveStatus
    started_at: datetime
    finished_at: datetime | None
    updated_at: datetime | None
    seconds: float | None
    report: dict | None
    ai_explanation: str | None
    # Arka plan ilerlemesi
    attempts: int
    best_placed: int
    required: int
    proven_infeasible: bool
    stop_requested: bool


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


class AiModelsIn(BaseModel):
    """Model listesi sorgusu. Alanlar boşsa kayıtlı ayarlar kullanılır."""
    base_url: str | None = None
    api_key: str | None = None


class AiModelsOut(BaseModel):
    models: list[str]
    # Listenin çekildiği adres — kullanıcıya nereye bağlanıldığını göstermek için.
    source: str
