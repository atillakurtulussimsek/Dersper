/** Tanıtım sayfasının kahraman görseli: kendini dolduran bir ders programı.
 *
 *  Ekran görüntüsü değil, uygulamanın kendi görsel diliyle kurulmuş gerçek bir
 *  ızgara. Dersler sırayla yerine oturur — ürünün vaadi (dağınıklıktan düzene)
 *  tek görselde anlatılır. Hareketi azalt tercihi açıkken çözülmüş hâliyle
 *  doğrudan görünür.
 */
const GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum"];
const SAATLER = ["08:30", "09:20", "10:10", "11:00", "11:50", "12:40"];

type Ders = { gun: number; saat: number; ad: string; ogretmen: string; renk: string };

// Gerçekçi bir 5-A haftası: bloklar, boşluklar ve tekrar eden dersler.
const DERSLER: Ders[] = [
  { gun: 0, saat: 0, ad: "Türkçe", ogretmen: "A. Yılmaz", renk: "#ef4444" },
  { gun: 0, saat: 1, ad: "Türkçe", ogretmen: "A. Yılmaz", renk: "#ef4444" },
  { gun: 0, saat: 3, ad: "Matematik", ogretmen: "Z. Demir", renk: "#3b82f6" },
  { gun: 0, saat: 4, ad: "Fen", ogretmen: "F. Şahin", renk: "#22c55e" },
  { gun: 1, saat: 0, ad: "Matematik", ogretmen: "Z. Demir", renk: "#3b82f6" },
  { gun: 1, saat: 1, ad: "Matematik", ogretmen: "Z. Demir", renk: "#3b82f6" },
  { gun: 1, saat: 2, ad: "İngilizce", ogretmen: "E. Aydın", renk: "#8b5cf6" },
  { gun: 1, saat: 4, ad: "Beden", ogretmen: "M. Aslan", renk: "#eab308" },
  { gun: 2, saat: 1, ad: "Fen", ogretmen: "F. Şahin", renk: "#22c55e" },
  { gun: 2, saat: 2, ad: "Fen", ogretmen: "F. Şahin", renk: "#22c55e" },
  { gun: 2, saat: 3, ad: "Sosyal", ogretmen: "E. Doğan", renk: "#f97316" },
  { gun: 2, saat: 5, ad: "Görsel", ogretmen: "S. Avlık", renk: "#ec4899" },
  { gun: 3, saat: 0, ad: "İngilizce", ogretmen: "E. Aydın", renk: "#8b5cf6" },
  { gun: 3, saat: 2, ad: "Türkçe", ogretmen: "A. Yılmaz", renk: "#ef4444" },
  { gun: 3, saat: 3, ad: "Türkçe", ogretmen: "A. Yılmaz", renk: "#ef4444" },
  { gun: 3, saat: 4, ad: "Din K.", ogretmen: "H. Yıldız", renk: "#14b8a6" },
  { gun: 4, saat: 1, ad: "Sosyal", ogretmen: "E. Doğan", renk: "#f97316" },
  { gun: 4, saat: 2, ad: "Matematik", ogretmen: "Z. Demir", renk: "#3b82f6" },
  { gun: 4, saat: 4, ad: "Türkçe", ogretmen: "A. Yılmaz", renk: "#ef4444" },
  { gun: 4, saat: 5, ad: "Beden", ogretmen: "M. Aslan", renk: "#eab308" },
];

const yerlesim = new Map(DERSLER.map((d) => [`${d.gun}:${d.saat}`, d]));

export default function TanitimIzgarasi() {
  return (
    <div className="overflow-hidden rounded-xl border border-cizgi bg-yuzey shadow-2xl shadow-murekkep/5">
      <div className="flex items-center justify-between border-b border-cizgi px-4 py-2.5">
        <span className="font-baslik text-sm font-semibold text-murekkep">5-A</span>
        <span className="sayisal text-2xs text-murekkep-silik">
          20 ders saati · 0,6 sn'de yerleşti
        </span>
      </div>

      <table className="w-full table-fixed border-collapse">
        <colgroup>
          <col className="w-14" />
          {GUNLER.map((g) => (
            <col key={g} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th className="border border-cizgi bg-yuzey-alt p-1" />
            {GUNLER.map((g) => (
              <th
                key={g}
                className="border border-cizgi bg-yuzey-alt px-1 py-1.5 text-2xs font-semibold text-murekkep-yumusak"
              >
                {g}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SAATLER.map((saat, s) => (
            <tr key={saat}>
              <th className="border border-cizgi bg-yuzey-alt px-1 py-1 text-center">
                <span className="sayisal block text-2xs font-semibold text-murekkep-yumusak">
                  {s + 1}.
                </span>
                <span className="sayisal block font-mono text-[8px] text-murekkep-silik">
                  {saat}
                </span>
              </th>
              {GUNLER.map((_, g) => {
                const ders = yerlesim.get(`${g}:${s}`);
                return (
                  <td
                    key={g}
                    className="h-11 border border-cizgi p-0.5 align-middle sm:h-12"
                  >
                    {ders && (
                      <div
                        className="yerlesen flex h-full w-full flex-col justify-center overflow-hidden rounded px-1 text-center"
                        style={{
                          background: `color-mix(in srgb, ${ders.renk} calc(var(--ders-zemin-alfa) * 100%), transparent)`,
                          boxShadow: `inset 3px 0 0 ${ders.renk}`,
                          // Sıralı yerleşme: gün gün, saat saat.
                          animationDelay: `${(g * SAATLER.length + s) * 45}ms`,
                        }}
                      >
                        <span className="truncate text-[10px] font-semibold leading-tight text-murekkep">
                          {ders.ad}
                        </span>
                        <span className="truncate text-[8.5px] leading-tight text-murekkep-yumusak">
                          {ders.ogretmen}
                        </span>
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
