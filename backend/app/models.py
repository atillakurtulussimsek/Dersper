"""Veri modeli.

Çok kurumlu: her kurum (`Institution`) kendi kullanıcıları, dönemleri ve
tanımlarıyla diğerlerinden yalıtılmıştır. Bir kullanıcı tam olarak bir kuruma
aittir; başka bir kurumda çalışmak için ayrı hesap gerekir.

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


class GapPolicy(str, enum.Enum):
    """Öğretmenin dersleri arasındaki boşluğa nasıl davranılacağı.

    Boşluk, bir öğretmenin bir gün içindeki ilk ve son dersi arasında kalan
    boş ders saatidir. Üç tercih de meşrudur; okul kendi düzenini seçer.
    """
    BOSLUKLU = "bosluklu"   # boşluk istenir — dersler güne yayılır
    IDEAL = "ideal"         # boşluğa bakılmaz (varsayılan, eski davranış)
    SIKI = "siki"           # boşluk en aza indirilir — gün sıkışır


class ConflictBasis(str, enum.Enum):
    """Çakışma neye göre ölçülür (bkz. `app.cakisma`).

    Kurum seçer: ızgaranın satırı mı esastır, gerçek saat aralığı mı?
    """
    DERS_SAATI = "ders_saati"   # Salı 3. ders yalnızca Salı 3. dersle çakışır
    SAAT = "saat"               # 09:00-09:40 ile 09:20-10:00 çakışır


class SectionOrder(str, enum.Enum):
    """Şubelerin listelerde hangi sırayla dizildiği (bkz. `app.siralama`)."""
    AD = "ad"       # sınıf seviyesi + doğal ad sırası (9-A < 10-A)
    ELLE = "elle"   # kullanıcının sürükleyip kaydettiği sıra


class SolveStatus(str, enum.Enum):
    BEKLIYOR = "bekliyor"
    CALISIYOR = "calisiyor"
    BASARILI = "basarili"
    COZUMSUZ = "cozumsuz"      # kısıtlar çelişiyor
    DURDURULDU = "durduruldu"  # kullanıcı iptal etti
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
    # institutions ↔ terms arasında döngüsel yabancı anahtar var; use_alter
    # ile bu kısıt tablolar kurulduktan sonra eklenir.
    active_term_id: Mapped[int | None] = mapped_column(
        ForeignKey("terms.id", ondelete="SET NULL", use_alter=True,
                   name="fk_institutions_active_term")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Term(Base, SoftDelete):
    """Öğretim dönemi. Tüm tanımlar bir döneme, dönem de bir kuruma bağlıdır."""

    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(150))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    # Açıkken bir öğretmen bir günde tek binada ders verir: binaların dersleri
    # ayrı günlere toplanır, gün içinde bina değiştirmek gerekmez.
    block_building_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    # "Aynı an" neye göre belirlenir: ızgaranın satırına mı, saat aralığına mı?
    # Düzenli tek ızgarası olan okulda satır zaten saatin kendisidir; saatleri
    # üst üste binebilen ızgaralarda (vardiya, farklı ders süreleri) aralık
    # ölçütü gerekir.
    conflict_basis: Mapped[ConflictBasis] = mapped_column(
        Enum(ConflictBasis), default=ConflictBasis.DERS_SAATI,
        server_default=ConflictBasis.DERS_SAATI.name,
    )
    # Şubeler nasıl sıralanır: ada göre (doğal) ya da elle verilen sırayla.
    section_order: Mapped[SectionOrder] = mapped_column(
        Enum(SectionOrder), default=SectionOrder.AD,
        server_default=SectionOrder.AD.name,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class User(Base):
    """Kurum kullanıcısı.

    E-posta sistem genelinde eşsizdir: bir hesap tek bir kuruma bağlıdır.
    Kurum içinde rol ayrımı yoktur; her kullanıcı yöneticidir.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE")
    )
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
    # Öğle arası. Teneffüsün özel hâli: ders konmaz, ayrıca günü sabah ve
    # öğleden sonra diye ikiye böler — öğretmenlerin yarım gün sınırı buna
    # dayanır. Günde en çok bir tane olabilir (uygulama katmanında denetlenir).
    is_lunch: Mapped[bool] = mapped_column(Boolean, default=False)

    day: Mapped[Day] = relationship(back_populates="periods")


class Teacher(Base, SoftDelete):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(200))
    short_code: Mapped[str | None] = mapped_column(String(20))
    branch: Mapped[str | None] = mapped_column(String(100))
    max_daily_hours: Mapped[int | None] = mapped_column(Integer)
    # Haftada okulda bulunabileceği en fazla süre, YARIM GÜN olarak.
    # 9 = 4,5 gün. Yarım günler tam sayıyla tutulur: kesirli gün yalnızca
    # yarımı kabul ettiği için ikiye katlamak tam ve kesin bir birim verir.
    # NULL = sınır yok.
    max_half_days: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(7), default="#94a3b8")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    availability: Mapped[list[TeacherAvailability]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )

    @property
    def max_days(self) -> float | None:
        """Gün sınırı, kullanıcının konuştuğu birimde. Arayüz bunu okur."""
        return None if self.max_half_days is None else self.max_half_days / 2


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


class Building(Base, SoftDelete):
    """Bina. Bazı kurumlar birden fazla binada ders yapar.

    Şube kendi dersliğiyle birlikte bir binada durur; öğretmen ise binalar
    arasında gezer. Uzak binalarda gün içinde geçiş yapmak zor olduğu için
    dönem ayarıyla bu geçiş engellenebilir (bkz. `Term.block_building_switch`).
    """
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    short_code: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Section(Base, SoftDelete):
    """Şube — örn. 5-A."""
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))
    grade_level: Mapped[int | None] = mapped_column(Integer)
    student_count: Mapped[int | None] = mapped_column(Integer)
    # Şubenin dersliğinin bulunduğu bina. NULL = tek binalı kurum ya da
    # henüz atanmamış; bina kuralları bu şubeyi kısıtlamaz.
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Elle sıralamadaki yeri; NULL = sırası verilmemiş (sona düşer).
    sort_order: Mapped[int | None] = mapped_column(Integer)

    building: Mapped[Building | None] = relationship()

    curriculum: Mapped[list[CurriculumEntry]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )
    availability: Mapped[list[SectionAvailability]] = relationship(
        back_populates="section", cascade="all, delete-orphan"
    )


class CurriculumEntrySection(Base):
    """Birleşik dersin ek şubeleri.

    Bir müfredat satırı normalde tek şubeye aittir (`CurriculumEntry.section_id`).
    Birleşik derslerde — beden eğitimi, din kültürü, seçmeliler — birden fazla
    şube aynı saatte, aynı öğretmenle ders görür. O şubeler burada durur; asıl
    şube satırın kendisindedir, yani bu tablo yalnızca *ek* olanları tutar.

    Ayrı bir tablo olmasının sebebi kısmi birleşmedir: bir şube aynı dersi hem
    birleşik hem ayrı alabilir (2 saat 9-A+9-B birlikte, 1 saat ayrı). Bu da
    şube–ders eşsizliğini ortadan kaldırır; toplam saat denetimi onun yerini
    alır (bkz. app/routers/catalog.py).
    """
    __tablename__ = "curriculum_entry_sections"
    __table_args__ = (
        UniqueConstraint("entry_id", "section_id", name="uq_entry_section"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_entries.id", ondelete="CASCADE")
    )
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE")
    )

    section: Mapped[Section] = relationship()


class CurriculumEntry(Base, SoftDelete):
    """Bir şubede (ya da birleşik derslerde birkaç şubede), bir dersin, bir
    öğretmenle haftalık yükü.

    `section_id` asıl şubedir; birleşik derste ek şubeler `extra_sections`
    içindedir. Çakışma, gösterim ve müsaitlik hep `section_ids` üzerinden
    yürür — asıl/ek ayrımı yalnızca saklama biçimidir, kural değildir.
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
    extra_sections: Mapped[list[CurriculumEntrySection]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def sections(self) -> list[Section]:
        """Dersi birlikte gören şubeler; asıl şube başta."""
        return [self.section] + [e.section for e in self.extra_sections]

    @property
    def section_ids(self) -> list[int]:
        return [self.section_id] + [e.section_id for e in self.extra_sections]

    @property
    def birlesik(self) -> bool:
        return bool(self.extra_sections)


class Timetable(Base, SoftDelete):
    __tablename__ = "timetables"

    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    status: Mapped[TimetableStatus] = mapped_column(
        Enum(TimetableStatus), default=TimetableStatus.TASLAK
    )
    public_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    # Programa dahil şube kimlikleri. NULL = dönemin tüm şubeleri.
    section_ids: Mapped[list | None] = mapped_column(JSON)
    # Öğretmen boşluklarına nasıl davranılacağı. Üretimde kullanılır.
    gap_policy: Mapped[GapPolicy] = mapped_column(
        Enum(GapPolicy), default=GapPolicy.IDEAL
    )
    # Kullanıcının "görmezden gel" dediği uyarı anahtarları.
    ignored_warnings: Mapped[list | None] = mapped_column(JSON)
    # Programın şu an hangi sürümde durduğu. Geri/ileri alma bu imleci
    # sürüm ağacında gezdirir; ayrı bir adım yığını yoktur.
    current_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("timetable_versions.id", ondelete="SET NULL", use_alter=True,
                   name="fk_timetables_current_version")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="timetable", cascade="all, delete-orphan"
    )
    term: Mapped[Term] = relationship()
    versions: Mapped[list["TimetableVersion"]] = relationship(
        back_populates="timetable", cascade="all, delete-orphan",
        foreign_keys="TimetableVersion.timetable_id",
    )


class VersionKind(str, enum.Enum):
    ILK = "ilk"            # program açıldığında, boş hâli
    URETIM = "uretim"      # çözücü çıktısı
    ELLE = "elle"          # elle düzenleme


class TimetableVersion(Base):
    """Programın bir andaki tam hâli.

    Her değişiklik — üretim de, elle düzenleme de — yeni bir sürüm yazar.
    Sürümler EKLENİR, hiç silinmez: geri alıp başka bir yöne gitseniz de eski
    dal veritabanında durur ve listeden geri yüklenebilir.

    `parent_id` ağacı kurar: geri alma ebeveyne, ileri alma en yeni çocuğa
    gider. Böylece geri aldıktan sonra yapılan yeni değişiklik eski dalı
    silmeden yeni bir dal açar.
    """
    __tablename__ = "timetable_versions"
    __table_args__ = (
        UniqueConstraint("timetable_id", "number", name="uq_version_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(
        ForeignKey("timetables.id", ondelete="CASCADE")
    )
    # Program içinde 1'den başlayan, hiç tekrar etmeyen sıra numarası.
    number: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("timetable_versions.id", ondelete="SET NULL")
    )
    kind: Mapped[VersionKind] = mapped_column(Enum(VersionKind))
    # Ne olduğunu anlatan kısa Türkçe satır — geçmiş listesinde okunur.
    label: Mapped[str] = mapped_column(String(200))
    # Yerleşimlerin tamamı: [[curriculum_entry_id, period_id, kilitli], ...]
    placements: Mapped[list] = mapped_column(JSON)
    # Listede göstermek için; placements uzunluğuyla aynı.
    placed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    timetable: Mapped[Timetable] = relationship(
        back_populates="versions", foreign_keys=[timetable_id]
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
    """Bir program üretim çalıştırması.

    Çalıştırma arka planda sürer ve tam yerleşim sağlanana kadar birbiri ardına
    deneme yapar; `attempts` kaçıncı denemede olduğumuzu, `best_placed` o ana
    kadarki en iyi denemede kaç ders saatinin yerleştiğini tutar.
    """
    __tablename__ = "solve_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timetable_id: Mapped[int] = mapped_column(ForeignKey("timetables.id", ondelete="CASCADE"))
    status: Mapped[SolveStatus] = mapped_column(Enum(SolveStatus), default=SolveStatus.BEKLIYOR)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    seconds: Mapped[float | None] = mapped_column()
    report: Mapped[dict | None] = mapped_column(JSON)        # yapılandırılmış tanı
    ai_explanation: Mapped[str | None] = mapped_column(Text)  # sade Türkçe açıklama

    attempts: Mapped[int] = mapped_column(Integer, default=0)
    # En iyi denemede yerleşen ve toplamda yerleşmesi gereken ders saati.
    best_placed: Mapped[int] = mapped_column(Integer, default=0)
    required: Mapped[int] = mapped_column(Integer, default=0)
    # Çözücü, kısıtların çeliştiğini kanıtladı mı?
    proven_infeasible: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_requested: Mapped[bool] = mapped_column(Boolean, default=False)


class AiSettings(Base):
    """Kurumun kendi yapay zeka sağlayıcısı. Kurum başına tek satır."""
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), unique=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    base_url: Mapped[str | None] = mapped_column(String(300))
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(120), default="gpt-4o-mini")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())
