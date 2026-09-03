/** Günler ve ders saatleri. Ders saati sayısı güne göre değişebilir.
 *
 *  Satırlar tutamağından sürüklenerek yeniden sıralanır: araya teneffüs eklemek
 *  için sona bir satır ekleyip yerine çekmek yeter, aşağıdakileri tek tek
 *  kaydırmak gerekmez. Sıralama sunucuya ders saati KİMLİĞİYLE gider; böylece
 *  müsaitlik işaretleri, kaydığı yeni sıraya değil taşınan satırın peşinden
 *  gider.
 *
 *  Otomatik adlar ("3. ders", "Teneffüs", "Öğle arası") her yapısal
 *  değişiklikten sonra yeniden numaralanır; kullanıcının kendi yazdığı adlara
 *  dokunulmaz.
 */
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  DndContext, PointerSensor, closestCenter, useDraggable, useDroppable,
  useSensor, useSensors, type DragEndEvent, type DragStartEvent,
} from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Coffee, Download, GripVertical, Plus, Trash2, UtensilsCrossed,
} from "lucide-react";
import clsx from "clsx";

import {
  Buton, Girdi, Kart, Kutu, SayfaBasligi, Secim, Uyari, Yukleniyor,
} from "../components/ui";
import { get, post, put } from "../lib/api";
import { saatSorunlari } from "../lib/cakisma";
import { adlariTazele } from "../lib/izgara";
import type { CakismaOlcutu, Donem, Gun } from "../lib/types";

interface TaslakSaat {
  /** Sunucudaki kaydın kimliği; yeni satırlarda null. */
  id: number | null;
  /** React anahtarı ve sürükleme kimliği — sıra değişse de sabit kalır. */
  anahtar: string;
  name: string;
  start_time: string | null;
  end_time: string | null;
  is_break: boolean;
  is_lunch: boolean;
}

type TaslakGun = {
  index: number;
  name: string;
  is_active: boolean;
  periods: TaslakSaat[];
};

export default function ZamanIzgarasi() {
  const qc = useQueryClient();
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const [taslak, setTaslak] = useState<TaslakGun[]>([]);
  const [aktarimAcik, setAktarimAcik] = useState(false);
  const [kaynakId, setKaynakId] = useState<number | null>(null);
  // Yeni satırlara benzersiz yerel anahtar üretir.
  const sayac = useRef(0);

  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const gecmis = (donemler.data ?? []).filter((d) => !d.is_active);
  const aktifDonem = (donemler.data ?? []).find((d) => d.is_active);


  const izgarayiAktar = useMutation({
    mutationFn: () => post<Gun[]>(`/timegrid/import/${kaynakId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["timegrid"] });
      setAktarimAcik(false);
    },
  });

  useEffect(() => {
    if (!izgara.data) return;
    setTaslak(
      izgara.data.map((g) => ({
        index: g.index,
        name: g.name,
        is_active: g.is_active,
        periods: g.periods
          .slice()
          .sort((a, b) => a.index - b.index)
          .map((p) => ({
            id: p.id,
            anahtar: `s${p.id}`,
            name: p.name,
            start_time: p.start_time,
            end_time: p.end_time,
            is_break: p.is_break,
            is_lunch: p.is_lunch,
          })),
      })),
    );
  }, [izgara.data]);

  const kaydet = useMutation({
    mutationFn: () =>
      put<Gun[]>(
        "/timegrid",
        // `anahtar` yalnızca arayüze ait. Sıra listedeki konumdan yazılır;
        // kimlik de gittiği için sunucu satırı sırasından değil kendisinden tanır.
        taslak.map((g) => ({
          index: g.index,
          name: g.name,
          is_active: g.is_active,
          periods: g.periods.map((p, i) => ({
            id: p.id,
            index: i,
            name: p.name,
            start_time: p.start_time,
            end_time: p.end_time,
            is_break: p.is_break,
            is_lunch: p.is_lunch,
          })),
        })),
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timegrid"] }),
  });

  function gunuDegistir(index: number, yama: Partial<TaslakGun>) {
    setTaslak((t) => t.map((g) => (g.index === index ? { ...g, ...yama } : g)));
  }

  /** Bir günün saat listesini değiştirir ve otomatik adları tazeler. */
  function saatleriDegistir(
    gunIndex: number,
    islem: (saatler: TaslakSaat[]) => TaslakSaat[],
  ) {
    setTaslak((t) =>
      t.map((g) =>
        g.index === gunIndex ? { ...g, periods: adlariTazele(islem(g.periods)) } : g,
      ),
    );
  }

  function saatEkle(gunIndex: number) {
    sayac.current += 1;
    const anahtar = `y${sayac.current}`;
    saatleriDegistir(gunIndex, (s) => [
      ...s,
      {
        id: null,
        anahtar,
        // Otomatik kalıba uyan geçici ad; adlariTazele doğru numarayı yazar.
        name: "0. ders",
        start_time: null,
        end_time: null,
        is_break: false,
        is_lunch: false,
      },
    ]);
  }

  function saatSil(gunIndex: number, anahtar: string) {
    saatleriDegistir(gunIndex, (s) => s.filter((p) => p.anahtar !== anahtar));
  }

  function saatiDegistir(gunIndex: number, anahtar: string, yama: Partial<TaslakSaat>) {
    saatleriDegistir(gunIndex, (s) =>
      s.map((p) => (p.anahtar === anahtar ? { ...p, ...yama } : p)),
    );
  }

  /** Öğle arası günde tek olabilir: yenisi işaretlenince eskisi bırakılır.
   *  Öğle arasına ders konmadığı için teneffüs de olur. */
  function ogleArasiniDegistir(gunIndex: number, anahtar: string) {
    saatleriDegistir(gunIndex, (s) => {
      const acilacak = !s.find((p) => p.anahtar === anahtar)!.is_lunch;
      return s.map((p) =>
        p.anahtar === anahtar
          ? { ...p, is_lunch: acilacak, is_break: acilacak ? true : p.is_break }
          : { ...p, is_lunch: false },
      );
    });
  }

  /** Satırı, hedef satırın bulunduğu konuma taşır. */
  function satiriTasi(gunIndex: number, kaynak: string, hedef: string) {
    if (kaynak === hedef) return;
    saatleriDegistir(gunIndex, (s) => {
      const nereden = s.findIndex((p) => p.anahtar === kaynak);
      const nereye = s.findIndex((p) => p.anahtar === hedef);
      if (nereden < 0 || nereye < 0) return s;
      const kopya = [...s];
      const [tasinan] = kopya.splice(nereden, 1);
      kopya.splice(nereye, 0, tasinan);
      return kopya;
    });
  }

  /** Klavyeyle bir basamak yukarı/aşağı — sürüklemenin erişilebilir karşılığı. */
  function satiriKaydir(gunIndex: number, anahtar: string, yon: -1 | 1) {
    saatleriDegistir(gunIndex, (s) => {
      const i = s.findIndex((p) => p.anahtar === anahtar);
      const j = i + yon;
      if (i < 0 || j < 0 || j >= s.length) return s;
      const kopya = [...s];
      [kopya[i], kopya[j]] = [kopya[j], kopya[i]];
      return kopya;
    });
  }

  const toplam = taslak
    .filter((g) => g.is_active)
    .reduce((t, g) => t + g.periods.filter((p) => !p.is_break).length, 0);

  if (izgara.isLoading) return <Yukleniyor />;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Zaman Izgarası"
        aciklama="Hangi günlerde kaç ders saati olduğu. Teneffüse ders yerleştirilmez; öğle arası ayrıca günü sabah ve öğleden sonra diye böler."
        sag={
          <>
            <Buton
              tur="ikincil"
              onClick={() => {
                setKaynakId(gecmis[0]?.id ?? null);
                setAktarimAcik(true);
              }}
            >
              <Download className="h-4 w-4" /> Geçmiş dönemden aktar
            </Buton>
            <Buton onClick={() => kaydet.mutate()} yukleniyor={kaydet.isPending}>
              Kaydet
            </Buton>
          </>
        }
      />

      {kaydet.error && <Uyari tur="hata">{(kaydet.error as Error).message}</Uyari>}
      {kaydet.isSuccess && !kaydet.isPending && (
        <Uyari tur="basari">Zaman ızgarası kaydedildi.</Uyari>
      )}

      <Uyari>
        Haftada toplam <b>{toplam}</b> ders saati tanımlı. Satırları tutamağından
        sürükleyerek sıralayabilirsiniz. Yerleşmiş bir ders programı varken ızgara
        değiştirilemez; önce programı silmeniz gerekir.
      </Uyari>

      <Kutu
        acik={aktarimAcik}
        kapat={() => setAktarimAcik(false)}
        baslik="Geçmiş dönemden zaman ızgarası aktar"
      >
        <div className="space-y-4">
          <Uyari tur="hata">
            Bu dönemin mevcut zaman ızgarası <b>tamamen değiştirilir</b>. Yerleşmiş bir
            ders programı varsa işlem reddedilir.
          </Uyari>
          {!gecmis.length ? (
            <Uyari>Aktarılacak başka dönem yok.</Uyari>
          ) : (
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-murekkep-yumusak">
                Kaynak dönem
              </span>
              <Secim
                value={kaynakId ?? ""}
                onChange={(e) => setKaynakId(Number(e.target.value))}
              >
                {gecmis.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} · {d.counts.ders_saati ?? 0} gün
                  </option>
                ))}
              </Secim>
            </label>
          )}
          {izgarayiAktar.error && (
            <Uyari tur="hata">{(izgarayiAktar.error as Error).message}</Uyari>
          )}
          <div className="flex justify-end gap-2">
            <Buton tur="ikincil" onClick={() => setAktarimAcik(false)}>
              Vazgeç
            </Buton>
            <Buton
              tur="tehlike"
              disabled={!kaynakId}
              yukleniyor={izgarayiAktar.isPending}
              onClick={() => izgarayiAktar.mutate()}
            >
              Izgarayı değiştir
            </Buton>
          </div>
        </div>
      </Kutu>

      <div className="grid gap-4 lg:grid-cols-2">
        {taslak.map((g) => (
          <Kart
            key={g.index}
            baslik={g.name}
            aciklama={
              g.is_active
                ? `${g.periods.filter((p) => !p.is_break).length} ders · ${
                    g.periods.filter((p) => p.is_break).length
                  } teneffüs${g.periods.some((p) => p.is_lunch) ? " · öğle arası var" : ""}`
                : "Bu gün kapalı"
            }
            sag={
              <label className="flex items-center gap-2 text-sm text-murekkep-yumusak">
                <input
                  type="checkbox"
                  checked={g.is_active}
                  onChange={(e) => gunuDegistir(g.index, { is_active: e.target.checked })}
                  className="h-4 w-4 rounded border-cizgi-guclu"
                />
                Açık
              </label>
            }
          >
            {!g.is_active ? (
              <p className="text-sm text-murekkep-silik">Kapalı günlere ders yerleştirilmez.</p>
            ) : (
              <SaatDenetimi gun={g} olcut={aktifDonem?.conflict_basis} />
            )}
            {g.is_active && (
              <GunSaatleri
                gun={g}
                tasi={(kaynak, hedef) => satiriTasi(g.index, kaynak, hedef)}
                kaydir={(anahtar, yon) => satiriKaydir(g.index, anahtar, yon)}
                degistir={(anahtar, yama) => saatiDegistir(g.index, anahtar, yama)}
                ogleArasi={(anahtar) => ogleArasiniDegistir(g.index, anahtar)}
                sil={(anahtar) => saatSil(g.index, anahtar)}
                ekle={() => saatEkle(g.index)}
              />
            )}
          </Kart>
        ))}
      </div>
    </div>
  );
}

/** Girilen saatlerdeki tutarsızlıklar.
 *
 *  Saat bilgisi isteğe bağlıdır; girilmediğinde hiçbir şey söylenmez. Ama
 *  girildiyse ve tutarsızsa sessiz kalmak yanlış olur: seçili ölçüte göre ya
 *  beklenmedik bir çakışma doğar ya da gerçek bir çakışma görülmeden geçer.
 */
function SaatDenetimi({
  gun,
  olcut,
}: {
  gun: TaslakGun;
  olcut?: CakismaOlcutu;
}) {
  const sorunlar = saatSorunlari(gun.periods);
  if (!sorunlar.length) return null;

  const cakisanlar = sorunlar.filter((s) => s.tur === "cakisma");
  const otekiler = sorunlar.filter((s) => s.tur !== "cakisma");

  return (
    <div className="mb-3 space-y-2">
      {cakisanlar.length > 0 && (
        <Uyari tur={olcut === "saat" ? "bilgi" : "hata"}>
          <span className="block font-medium">
            {olcut === "saat"
              ? "Bu saatler çakışma sayılacak:"
              : "Bu saatler üst üste biniyor ama çakışma sayılmayacak:"}
          </span>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {cakisanlar.map((c) => (
              <li key={c.metin}>{c.metin}</li>
            ))}
          </ul>
          {olcut !== "saat" && (
            <span className="mt-1.5 block">
              Ölçüt <b>ders saati</b> olduğu için yalnızca aynı satır çakışma sayılır;
              aynı öğretmen bu iki satıra birden konabilir. Gerçek aralığa göre
              denetlensin istiyorsanız <Link to="/kisitlamalar" className="font-medium underline">Kısıtlamalar</Link>{" "}
              sayfasından <b>saat aralığı</b> ölçütünü seçin.
            </span>
          )}
        </Uyari>
      )}
      {otekiler.length > 0 && (
        <Uyari tur="hata">
          <ul className="list-disc space-y-0.5 pl-4">
            {otekiler.map((c) => (
              <li key={c.metin}>{c.metin}</li>
            ))}
          </ul>
        </Uyari>
      )}
    </div>
  );
}

function GunSaatleri({
  gun,
  tasi,
  kaydir,
  degistir,
  ogleArasi,
  sil,
  ekle,
}: {
  gun: TaslakGun;
  tasi: (kaynak: string, hedef: string) => void;
  kaydir: (anahtar: string, yon: -1 | 1) => void;
  degistir: (anahtar: string, yama: Partial<TaslakSaat>) => void;
  ogleArasi: (anahtar: string) => void;
  sil: (anahtar: string) => void;
  ekle: () => void;
}) {
  const [suruklenen, setSuruklenen] = useState<string | null>(null);
  // Küçük bir eşik: tutamağa tıklamak sürükleme sayılmasın.
  const sensorler = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  );

  function bittiginde(e: DragEndEvent) {
    setSuruklenen(null);
    if (e.over) tasi(String(e.active.id), String(e.over.id));
  }

  return (
    <DndContext
      sensors={sensorler}
      collisionDetection={closestCenter}
      onDragStart={(e: DragStartEvent) => setSuruklenen(String(e.active.id))}
      onDragEnd={bittiginde}
      onDragCancel={() => setSuruklenen(null)}
    >
      <div className="space-y-2">
        {gun.periods.map((p, i) => (
          <SaatSatiri
            key={p.anahtar}
            saat={p}
            sira={i + 1}
            ilk={i === 0}
            son={i === gun.periods.length - 1}
            suruklenen={suruklenen}
            kaydir={kaydir}
            degistir={degistir}
            ogleArasi={ogleArasi}
            sil={sil}
          />
        ))}

        <div className="flex gap-2 pt-1">
          <Buton tur="ikincil" onClick={ekle}>
            <Plus className="h-4 w-4" /> Saat ekle
          </Buton>
        </div>
      </div>
    </DndContext>
  );
}

function SaatSatiri({
  saat,
  sira,
  ilk,
  son,
  suruklenen,
  kaydir,
  degistir,
  ogleArasi,
  sil,
}: {
  saat: TaslakSaat;
  sira: number;
  ilk: boolean;
  son: boolean;
  suruklenen: string | null;
  kaydir: (anahtar: string, yon: -1 | 1) => void;
  degistir: (anahtar: string, yama: Partial<TaslakSaat>) => void;
  ogleArasi: (anahtar: string) => void;
  sil: (anahtar: string) => void;
}) {
  const { attributes, listeners, setNodeRef: tutamak } = useDraggable({ id: saat.anahtar });
  const { setNodeRef: hedef, isOver } = useDroppable({ id: saat.anahtar });
  const kendisi = suruklenen === saat.anahtar;

  return (
    <div
      ref={hedef}
      className={clsx(
        "flex items-center gap-2 rounded-lg transition-colors",
        kendisi && "opacity-40",
        isOver && !kendisi && "bg-yuzey-alt ring-1 ring-cizgi-guclu",
      )}
    >
      <button
        ref={tutamak}
        {...listeners}
        {...attributes}
        type="button"
        title="Sürükleyerek taşıyın — yukarı/aşağı ok tuşları da çalışır"
        // Sürükleme yalnızca işaretçiyle çalışıyor; klavye karşılığı bu.
        onKeyDown={(e) => {
          if (e.key === "ArrowUp" && !ilk) {
            e.preventDefault();
            kaydir(saat.anahtar, -1);
          } else if (e.key === "ArrowDown" && !son) {
            e.preventDefault();
            kaydir(saat.anahtar, 1);
          }
        }}
        className="shrink-0 cursor-grab rounded-md p-1 text-murekkep-silik hover:bg-yuzey-alt hover:text-murekkep-yumusak active:cursor-grabbing"
      >
        <GripVertical className="h-4 w-4" />
      </button>

      <span className="sayisal w-4 shrink-0 text-right text-xs text-murekkep-silik">
        {sira}
      </span>

      <Girdi
        value={saat.name}
        onChange={(e) => degistir(saat.anahtar, { name: e.target.value })}
        className="min-w-0 flex-1"
      />
      <Girdi
        type="time"
        value={saat.start_time?.slice(0, 5) ?? ""}
        onChange={(e) => degistir(saat.anahtar, { start_time: e.target.value || null })}
        className="w-[104px] shrink-0"
      />
      <Girdi
        type="time"
        value={saat.end_time?.slice(0, 5) ?? ""}
        onChange={(e) => degistir(saat.anahtar, { end_time: e.target.value || null })}
        className="w-[104px] shrink-0"
      />

      <button
        type="button"
        title={saat.is_break ? "Teneffüs — ders konmaz" : "Ders saati"}
        onClick={() =>
          degistir(saat.anahtar, {
            is_break: !saat.is_break,
            // Öğle arası zaten teneffüstür; teneffüsü kapatmak onu da kaldırır.
            is_lunch: saat.is_break ? false : saat.is_lunch,
          })
        }
        className={clsx(
          "shrink-0 rounded-lg border p-2",
          saat.is_break
            ? "border-uyari/25 bg-uyari-zemin text-uyari"
            : "border-cizgi-guclu bg-yuzey text-murekkep-silik hover:bg-yuzey-alt",
        )}
      >
        <Coffee className="h-4 w-4" />
      </button>
      <button
        type="button"
        title={
          saat.is_lunch
            ? "Öğle arası — günü sabah ve öğleden sonra diye böler"
            : "Öğle arası yap"
        }
        onClick={() => ogleArasi(saat.anahtar)}
        className={clsx(
          "shrink-0 rounded-lg border p-2",
          saat.is_lunch
            ? "border-cizgi-guclu bg-murekkep text-uzeri"
            : "border-cizgi-guclu bg-yuzey text-murekkep-silik hover:bg-yuzey-alt",
        )}
      >
        <UtensilsCrossed className="h-4 w-4" />
      </button>
      <button
        type="button"
        title="Bu satırı sil"
        aria-label="Satırı sil"
        onClick={() => sil(saat.anahtar)}
        className="shrink-0 rounded-lg border border-cizgi-guclu bg-yuzey p-2 text-murekkep-silik hover:bg-yuzey-alt hover:text-hata"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}
