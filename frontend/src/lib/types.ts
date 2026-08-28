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

export interface Donem {
  id: number;
  name: string;
  starts_on: string | null;
  ends_on: string | null;
  created_at: string;
  is_active: boolean;
  counts: Record<string, number>;
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
  is_active: boolean;
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
}

export interface Program {
  id: number;
  name: string;
  status: ProgramDurumu;
  public_token: string | null;
  created_at: string;
}

export interface Hucre {
  assignment_id: number;
  period_id: number;
  day_index: number;
  period_index: number;
  section_id: number;
  section_name: string;
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
  tur: "gunluk_asim" | "bitisik";
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
