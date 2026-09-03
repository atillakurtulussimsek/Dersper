/** Backend şemalarının karşılığı. */

export type KurumTipi = "k12" | "kurs";
export type Musaitlik = "uygun" | "uygun_degil" | "tercih";
export type ProgramDurumu = "taslak" | "uretildi" | "yayinda";
export type DenemeDurumu =
  | "bekliyor"
  | "calisiyor"
  | "basarili"
  | "cozumsuz"
  | "durduruldu"
  | "hata";

export interface OturumDurumu {
  has_institutions: boolean;
  registration_open: boolean;
}

/** Çakışma ölçütü — bkz. lib/cakisma.ts ve backend app/cakisma.py. */
export type CakismaOlcutu = "ders_saati" | "saat";

export interface Donem {
  id: number;
  name: string;
  starts_on: string | null;
  ends_on: string | null;
  /** Açıkken bir öğretmen bir günde tek binada ders verir. */
  block_building_switch: boolean;
  /** Çakışma neye göre ölçülür: ızgaranın satırı mı, gerçek saat aralığı mı? */
  conflict_basis: CakismaOlcutu;
  /** Şubeler ada göre mi, elle verilen sırayla mı dizilir? */
  section_order: "ad" | "elle";
  created_at: string;
  is_active: boolean;
  counts: Record<string, number>;
}

export interface Bina {
  id: number;
  name: string;
  short_code: string | null;
  notes: string | null;
  is_active: boolean;
}

export interface AktarimSonucu {
  imported: number;
  skipped: string[];
}

export interface Kullanici {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface Kurum {
  id: number;
  name: string;
  type: KurumTipi;
  address: string | null;
}

export interface DersSaati {
  id: number;
  day_id: number;
  index: number;
  name: string;
  start_time: string | null;
  end_time: string | null;
  is_break: boolean;
  /** Öğle arası: teneffüsün, günü sabah ve öğleden sonra diye bölen hâli. */
  is_lunch: boolean;
}

export interface Gun {
  id: number;
  index: number;
  name: string;
  is_active: boolean;
  periods: DersSaati[];
}

export interface Ogretmen {
  id: number;
  full_name: string;
  short_code: string | null;
  branch: string | null;
  max_daily_hours: number | null;
  /** Haftada okulda bulunabileceği en fazla gün. Yarım kabul edilir (4.5). */
  max_days: number | null;
  notes: string | null;
  color: string;
  is_active: boolean;
}

export interface Ders {
  id: number;
  name: string;
  short_code: string | null;
  color: string;
  is_active: boolean;
}

export interface Sube {
  id: number;
  name: string;
  grade_level: number | null;
  student_count: number | null;
  /** Dersliğinin bulunduğu bina; null = tek binalı kurum. */
  building_id: number | null;
  is_active: boolean;  /** Elle sıralamadaki yeri; null = sırası verilmemiş. */
  sort_order: number | null;
}


export interface MufredatSatiri {
  id: number;
  section_id: number;
  subject_id: number;
  teacher_id: number;
  weekly_hours: number;
  /** Haftalık saatin gün içindeki parçalanışı, örn. "2+2+1". */
  block_pattern: string;
  max_per_day: number;
  subject: Ders;
  teacher: Ogretmen;
  section: Sube;
  /** Dersi birlikte gören şubeler; asıl şube başta. Birden fazlaysa birleşik. */
  sections: Sube[];
}

/** Öğretmenin dersleri arasındaki boşluğa nasıl davranılacağı. */
export type BoslukPolitikasi = "bosluklu" | "ideal" | "siki";

export interface Program {
  id: number;
  name: string;
  status: ProgramDurumu;
  public_token: string | null;
  /** Programa dahil şubeler; null = dönemin tüm şubeleri. */
  section_ids: number[] | null;
  gap_policy: BoslukPolitikasi;
  created_at: string;
}

/** Dönemin kapalı saatleri: kayıt kimliği -> ders saati kimlikleri. */
export interface KapaliSaatler {
  teachers: Record<number, number[]>;
  sections: Record<number, number[]>;
}

export interface Hucre {
  assignment_id: number;
  period_id: number;
  day_index: number;
  period_index: number;
  section_id: number;
  section_name: string;
  /** Dersi birlikte gören şubeler. Birden fazlaysa birleşik ders. */
  section_ids: number[];
  section_names: string[];
  subject_name: string;
  subject_short: string | null;
  subject_color: string;
  teacher_id: number;
  teacher_name: string;
  teacher_short: string | null;
  is_locked: boolean;
}

export interface ProgramUyarisi {
  key: string;
  tur: "gunluk_asim" | "bitisik" | "gun_siniri" | "bina_gecisi";
  baslik: string;
  detay: string;
  sube: string;
  ders: string;
  ogretmen: string;
  gun: string;
  konan: number;
  sinir: number;
  ignored: boolean;
}

export interface Izgara {
  timetable: Program;
  cells: Hucre[];
  /** Geri/ileri alınacak sürüm var mı. */
  can_undo: boolean;
  can_redo: boolean;
  /** Programın durduğu sürüm numarası. */
  version: number | null;  /** Dönemin şubeleri, kurumun seçtiği sırayla. */
  section_names: string[];
}


export type SurumTuru = "ilk" | "uretim" | "elle";

/** Geçmiş listesindeki tek bir sürüm. */
export interface Surum {
  number: number;
  kind: SurumTuru;
  label: string;
  placed: number;
  created_at: string;
}

export interface FarkKonum {
  period_id: number;
  gun: string;
  saat: string;
  gun_index: number;
  period_index: number;
}

export type FarkTuru = "tasindi" | "cikti" | "eklendi" | "kilitlendi" | "kilit_acildi";

export interface FarkDegisikligi {
  tur: FarkTuru;
  entry_id: number;
  sube: string;
  ders: string;
  ogretmen: string;
  kaynak: FarkKonum | null;
  hedef: FarkKonum | null;
}

/** İki sürüm arasındaki fark: A'dan B'ye. */
export interface SurumFarki {
  a: Surum;
  b: Surum;
  ozet: { tasindi: number; cikti: number; eklendi: number; kilit: number; degisen_ders: number };
  degisiklikler: FarkDegisikligi[];
}

/** Sürüklenen ders için tek bir saatin değerlendirmesi. */
export interface Hedef {
  period_id: number;
  uygun: boolean;
  neden: string | null;
}

/** Sürüklenmekte olan şey: ızgaradaki bir blok ya da raftaki bekleyen blok. */
export type Suruklenen =
  | { tur: "hucre"; assignmentId: number; hucreler: Hucre[] }
  | { tur: "bekleyen"; entryId: number; uzunluk: number; etiket: string; renk: string };

/** Bekleyenler rafındaki tek bir blok. */
export interface BekleyenBlok {
  curriculum_entry_id: number;
  uzunluk: number;
  section_name: string;
  subject_name: string;
  subject_color: string;
  teacher_name: string;
}

export interface Bulgu {
  kod: string;
  baslik: string;
  detay: string;
  onem: "engel" | "uyari";
  sube?: string;
  ders?: string;
  ogretmen?: string;
  gereken?: number;
  mevcut?: number;
}

/** Çözümsüzlükte çelişen tek bir kısıt ve çözüm önerisi. */
export interface Sikisiklik {
  tur: "ogretmen" | "sube";
  metin: string;
  oneri: string;
  /** yük / açık saat, yüzde. */
  oran: number;
}

export interface Celiski {
  tur: string;
  metin: string;
  oneri: string;
  /** true: yalnız bunu değiştirmek yeter · false: yetmez · null: bilinmiyor. */
  tek_basina_yeterli: boolean | null;
}

export interface Rapor {
  durum: string;
  sure_sn: number;
  ozet: {
    ders_saati_sayisi: number;
    gun_sayisi: number;
    ders_atamasi: number;
    toplam_ders_saati: number;
    sube_sayisi: number;
    ogretmen_sayisi: number;
    yerlesmeyen_toplam: number;
  };
  bulgular: Bulgu[];
  celiskiler: Celiski[];
  /** Kesin çelişki yoksa: yerleşemeyen derslerin en sıkışık kaynakları. */
  sikisiklik?: Sikisiklik[];
  yerlesmeyenler: {
    sube: string;
    ders: string;
    ogretmen: string;
    istenen_saat: number;
    yerlesmeyen_saat: number;
  }[];
}

export interface Deneme {
  id: number;
  timetable_id: number;
  status: DenemeDurumu;
  started_at: string;
  finished_at: string | null;
  updated_at: string | null;
  seconds: number | null;
  report: Rapor | null;
  ai_explanation: string | null;
  /** Kaçıncı denemede olunduğu. */
  attempts: number;
  /** En iyi denemede yerleşen ve toplamda gereken ders saati. */
  best_placed: number;
  required: number;
  /** Çözücü kısıtların çeliştiğini kanıtladı mı? */
  proven_infeasible: boolean;
  stop_requested: boolean;
}

export interface ModelListesi {
  models: string[];
  source: string;
}

export interface YapayZekaAyarlari {
  enabled: boolean;
  base_url: string | null;
  model: string;
  api_key_masked: string;
  has_api_key: boolean;
}
