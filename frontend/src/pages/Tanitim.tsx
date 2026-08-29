/** Tanıtım sayfası — girişsiz ziyaretçilerin gördüğü ana sayfa.
 *
 *  Uygulamanın tasarım belirteçlerini aynen kullanır: ayrı bir "pazarlama
 *  kimliği" yok, ziyaretçi tanıtımda gördüğü arayüzün aynısını kullanmaya
 *  başlıyor. Ekran görüntüsü de yok; parçalar gerçek HTML olarak kurulur,
 *  böylece her iki temada doğru görünür ve arayüz değiştikçe bayatlamaz.
 *
 *  Dürüstlük kuralı: burada yalnızca yapılmış işler anlatılır. Boşluk
 *  eniyilemesi, vekalet, nöbet çizelgesi ve e-Okul entegrasyonu henüz yok;
 *  sayfa bunların varmış gibi okunmasına izin vermemeli.
 */
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, Minus } from "lucide-react";

import TanitimIzgarasi from "../components/TanitimIzgarasi";
import TemaSecici from "../components/TemaSecici";
import { Buton } from "../components/ui";
import { get } from "../lib/api";
import type { OturumDurumu } from "../lib/types";

const DEPO = "https://github.com/atillakurtulussimsek/Dersper";

const ADIMLAR = [
  {
    baslik: "Tanımları girin",
    metin:
      "Öğretmenler, dersler, şubeler ve haftalık ders saatleri. Öğretmenin " +
      "gelemediği saatleri ve şubenin yalnızca sabah ya da akşam ders " +
      "gördüğünü işaretlersiniz.",
  },
  {
    baslik: "Programı üretin",
    metin:
      "Çözücü arka planda çalışır; siz başka işinize bakabilirsiniz. Kaç " +
      "deneme yapıldığını ve ne kadar süredir çalıştığını ekrandan izlersiniz.",
  },
  {
    baslik: "Düzenleyin ve yayınlayın",
    metin:
      "Hücreleri sürükleyerek elle oynayın; çakışma yaratan taşımalar " +
      "reddedilir. Sonra PDF, Excel ya da girişsiz bir bağlantı olarak paylaşın.",
  },
];

const OZELLIKLER = [
  {
    baslik: "Kısıt tabanlı üretim",
    metin:
      "Google OR-Tools CP-SAT çözücüsü. Öğretmen ve şube çakışması, müsaitlik " +
      "matrisi, blok dersler ve günlük tekrar sınırı aynı anda gözetilir.",
  },
  {
    baslik: "Serbest ders dağılımı",
    metin:
      "5 saatlik bir dersi 2+2+1 ya da 3+2 olarak bölersiniz. Bloklar gün " +
      "içinde ardışık saatlere oturur.",
  },
  {
    baslik: "Bir derse birden çok öğretmen",
    metin:
      "İngilizce'nin 2 saati bir, 2 saati başka öğretmende olabilir. Aynı " +
      "şubede aynı ders farklı öğretmenlerle tanımlanır.",
  },
  {
    baslik: "Dönemler",
    metin:
      "Her dönem kendi kadrosu, dersleri ve programlarıyla bağımsızdır. Yeni " +
      "dönemde geçmiş dönemden istediğiniz kayıtları seçip aktarırsınız.",
  },
  {
    baslik: "Çarşaf liste ve çıktılar",
    metin:
      "Şube ya da öğretmen bazında ayrı sayfalar, ya da hepsi tek sayfada " +
      "çarşaf liste. PDF, Excel ve yazdırma.",
  },
  {
    baslik: "Çok kullanıcılı",
    metin:
      "Kurumunuza istediğiniz kadar hesap açarsınız. Her kurum kendi " +
      "verisiyle yalıtılmıştır.",
  },
];

const KARSILASTIRMA = {
  basliklar: ["", "Dersper", "aSc", "ProgMatik", "Bilsa", "Yabil"],
  satirlar: [
    { ad: "Ücret", degerler: ["Ücretsiz", "Ücretli", "Ücretli", "Ücretli", "Ücretli"] },
    {
      ad: "Kaynak kodu",
      degerler: ["Açık (AGPL-3.0)", "Kapalı", "Kapalı", "Kapalı", "Kapalı"],
    },
    {
      ad: "Planlama ortamı",
      degerler: ["Tarayıcı", "Masaüstü", "Masaüstü", "Masaüstü", "Masaüstü"],
    },
    {
      ad: "Kendi sunucunuzda barındırma",
      degerler: [true, false, false, false, false],
    },
    {
      ad: "Yerleşmeyeni sade dille açıklama",
      degerler: [true, false, false, false, false],
    },
  ],
};

const SORULAR = [
  {
    soru: "Verilerimiz nerede duruyor?",
    cevap:
      "Kendi sunucunuzda. Dersper'i kendi makinenize kurarsanız veritabanı " +
      "da sizde olur; kimse dışarıdan erişemez.",
  },
  {
    soru: "Yapay zeka zorunlu mu?",
    cevap:
      "Hayır. Kapalıyken program üretimi ve diğer her şey aynı şekilde " +
      "çalışır; yalnızca tıkanma anındaki sade Türkçe açıklama devre dışı " +
      "kalır. Açacaksanız kendi API anahtarınızı Ayarlar'dan girersiniz — biz " +
      "bir anahtar sağlamayız ve anahtarınız sunucunuzdan çıkmaz.",
  },
  {
    soru: "Kaç şubeye kadar kullanılabilir?",
    cevap:
      "12 şube ve 16 öğretmenlik bir okulun haftalık programı (324 ders saati) " +
      "bir saniyenin altında üretiliyor. Daha büyük okullarda süre uzar; " +
      "üretim arka planda çalıştığı için ekranı beklemeniz gerekmez.",
  },
  {
    soru: "Hangi özellikler henüz yok?",
    cevap:
      "Öğretmen boşluklarını en aza indirme, vekalet (dolduran öğretmen), " +
      "nöbet çizelgesi, derslik/bina yönetimi ve e-Okul entegrasyonu henüz " +
      "yok. Bunlar sonraki sürümlerde planlanıyor.",
  },
];

function Bolum({
  etiket,
  baslik,
  aciklama,
  children,
}: {
  etiket: string;
  baslik: string;
  aciklama?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-cizgi py-16 sm:py-20">
      <div className="mx-auto max-w-6xl px-6">
        <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-murekkep-silik">
          {etiket}
        </p>
        <h2 className="mt-2 max-w-2xl font-baslik text-2xl font-semibold tracking-tight text-murekkep sm:text-3xl">
          {baslik}
        </h2>
        {aciklama && (
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-murekkep-yumusak">
            {aciklama}
          </p>
        )}
        <div className="mt-10">{children}</div>
      </div>
    </section>
  );
}

export default function Tanitim() {
  const durum = useQuery({
    queryKey: ["auth-status"],
    queryFn: () => get<OturumDurumu>("/auth/status"),
    retry: 1,
  });
  const kayitAcik = durum.data?.registration_open ?? false;

  return (
    <div className="min-h-screen bg-kagit">
      <header className="sticky top-0 z-30 border-b border-cizgi bg-kagit/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <span className="font-baslik text-lg font-semibold tracking-tight text-murekkep">
            Dersper
          </span>
          <div className="flex items-center gap-2">
            <TemaSecici />
            <a
              href={DEPO}
              target="_blank"
              rel="noreferrer"
              className="hidden rounded-lg px-3 py-1.5 text-sm text-murekkep-yumusak transition-colors hover:text-murekkep sm:block"
            >
              GitHub
            </a>
            <Link to="/giris">
              <Buton tur="ikincil">Giriş yap</Buton>
            </Link>
          </div>
        </div>
      </header>

      {/* Kahraman: vaadin kendisi. Ekran görüntüsü yerine çalışan bir ızgara. */}
      <section className="mx-auto max-w-6xl px-6 py-16 sm:py-24">
        <div className="grid items-center gap-12 lg:grid-cols-[1fr_minmax(0,1.05fr)]">
          <div>
            <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-murekkep-silik">
              Açık kaynak ders dağıtım programı
            </p>
            {/* Satır kırılması tarayıcıya dengeletilir; elle <br /> koymak
              * farklı genişliklerde dağınık duruyordu. */}
            <h1 className="mt-3 text-balance font-baslik text-4xl font-semibold leading-[1.08] tracking-tight text-murekkep sm:text-5xl">
              Okulunuzun ders programı, haftalarca değil saniyeler içinde.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-murekkep-yumusak">
              Öğretmen müsaitliklerini ve haftalık ders yükünü girin; Dersper
              çakışmasız programı kendisi kursun. Yerleştiremediği bir ders
              olursa sebebini sade Türkçeyle anlatır.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              {kayitAcik ? (
                <Link to="/kayit">
                  <Buton className="px-5 py-2.5 text-base">
                    Ücretsiz kurum hesabı açın
                    <ArrowRight className="h-4 w-4" />
                  </Buton>
                </Link>
              ) : (
                <Link to="/giris">
                  <Buton className="px-5 py-2.5 text-base">
                    Giriş yap
                    <ArrowRight className="h-4 w-4" />
                  </Buton>
                </Link>
              )}
              <a href={DEPO} target="_blank" rel="noreferrer">
                <Buton tur="ikincil" className="px-4 py-2.5 text-base">
                  Kendi sunucunuza kurun
                </Buton>
              </a>
            </div>

            <p className="mt-4 text-sm text-murekkep-silik">
              Kredi kartı yok, deneme süresi yok. AGPL-3.0 lisanslı, tamamen
              açık kaynak.
            </p>
          </div>

          <TanitimIzgarasi />
        </div>
      </section>

      <Bolum
        etiket="Sorun"
        baslik="Ders programı elde haftalar alıyor."
        aciklama="Bir öğretmenin saatini değiştirirsiniz, üç şubede çakışma çıkar. Bu işi kolaylaştıran programlar ise ücretli, Windows'a bağlı ve tek bilgisayarda çalışıyor. Neden yerleştiremediklerini de söylemiyorlar — yalnızca “olmadı” diyorlar."
      >
        <div className="overflow-x-auto rounded-xl border border-cizgi bg-yuzey">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-cizgi text-left">
                {KARSILASTIRMA.basliklar.map((b, i) => (
                  <th
                    key={b || i}
                    className={
                      i === 1
                        ? "px-4 py-3 font-baslik text-sm font-semibold text-murekkep"
                        : "px-4 py-3 text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik"
                    }
                  >
                    {b}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-cizgi">
              {KARSILASTIRMA.satirlar.map((satir) => (
                <tr key={satir.ad}>
                  <td className="px-4 py-3 text-murekkep-yumusak">{satir.ad}</td>
                  {satir.degerler.map((d, i) => (
                    <td
                      key={i}
                      className={
                        i === 0
                          ? "bg-yuzey-alt px-4 py-3 font-medium text-murekkep"
                          : "px-4 py-3 text-murekkep-silik"
                      }
                    >
                      {typeof d === "boolean" ? (
                        d ? (
                          <Check className="h-4 w-4 text-basari" aria-label="var" />
                        ) : (
                          <Minus className="h-4 w-4 text-murekkep-silik" aria-label="yok" />
                        )
                      ) : (
                        d
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-murekkep-silik">
          Rakip bilgileri üreticilerin herkese açık tanıtım sayfalarından
          derlenmiştir ve değişebilir. Karşılaştırma planlama uygulamasının
          kendisini kapsar; bu ürünlerin ayrıca mobil ya da yayın uygulamaları
          olabilir.
        </p>
      </Bolum>

      <Bolum
        etiket="Nasıl çalışır"
        baslik="Üç adım."
      >
        <ol className="grid gap-6 sm:grid-cols-3">
          {ADIMLAR.map((a, i) => (
            <li key={a.baslik} className="rounded-xl border border-cizgi bg-yuzey p-5">
              {/* Burada numara gerçekten sıra bildiriyor: adımlar birbirini izler. */}
              <span className="sayisal font-baslik text-2xl font-semibold text-murekkep-silik">
                {i + 1}
              </span>
              <h3 className="mt-2 font-baslik text-base font-semibold text-murekkep">
                {a.baslik}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-murekkep-yumusak">
                {a.metin}
              </p>
            </li>
          ))}
        </ol>
      </Bolum>

      {/* Ayırt edici özellik: tıkanmayı açıklamak. Rakiplerin hiçbirinde yok. */}
      <Bolum
        etiket="Ayırt edici"
        baslik="Program yerleşmediğinde nedenini söyler."
        aciklama="Çözücü tıkandığında hangi kısıtın sıkıştırdığını sayısal olarak çıkarır. Yapay zekayı açarsanız bunu okul yönetimine hitap eden sade bir Türkçeyle anlatır ve neyi gevşetmeniz gerektiğini önerir."
      >
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-xl border border-hata/25 bg-hata-zemin p-5">
            <p className="text-2xs font-semibold uppercase tracking-[0.08em] text-hata">
              Tespit
            </p>
            <p className="mt-2 font-baslik text-base font-semibold text-hata">
              Ayşe Yılmaz öğretmenin yükü müsait saatlerini aşıyor
            </p>
            <p className="mt-2 text-sm leading-relaxed text-hata/90">
              Toplam 26 saat ders veriyor, ama müsaitlik matrisine göre haftada
              yalnızca 24 saati uygun. 2 saat açık var.
            </p>
          </div>
          <div className="rounded-xl border border-cizgi bg-yuzey p-5">
            <p className="text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik">
              Yapay zeka yorumu
            </p>
            <p className="mt-2 text-sm leading-relaxed text-murekkep-yumusak">
              <span className="font-medium text-murekkep">
                Programın tıkanma sebebi tek bir öğretmenin fazla yüklenmiş
                olması.
              </span>{" "}
              Ayşe Yılmaz'ın cuma günü tamamen kapalı görünüyor; o günü açmanız
              ya da 5-B şubesindeki Türkçe dersinin 2 saatini başka bir
              öğretmene devretmeniz yeterli.
            </p>
            <p className="mt-3 text-xs text-murekkep-silik">
              Kendi API anahtarınızla çalışır. Kapalıyken program üretimi aynen
              sürer.
            </p>
          </div>
        </div>
      </Bolum>

      <Bolum etiket="Neler var" baslik="Bugün çalışan özellikler.">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {OZELLIKLER.map((o) => (
            <div key={o.baslik} className="rounded-xl border border-cizgi bg-yuzey p-5">
              <h3 className="font-baslik text-base font-semibold text-murekkep">
                {o.baslik}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-murekkep-yumusak">
                {o.metin}
              </p>
            </div>
          ))}
        </div>
      </Bolum>

      <Bolum
        etiket="Açık kaynak"
        baslik="Kendi sunucunuza kurun."
        aciklama="Dersper AGPL-3.0 lisanslıdır ve kapalı kaynak hiçbir parçası yoktur. Docker ile tek komutta ayağa kalkar; veritabanınız ve yapay zeka anahtarınız sizde kalır."
      >
        <div className="overflow-hidden rounded-xl border border-cizgi bg-yuzey">
          <pre className="overflow-x-auto p-5 font-mono text-xs leading-relaxed text-murekkep-yumusak">
            <code>{`git clone ${DEPO}.git
cd Dersper
cp .env.example .env      # veritabanı bilgilerinizi girin
docker compose up -d --build`}</code>
          </pre>
        </div>
        <div className="mt-5">
          <a href={DEPO} target="_blank" rel="noreferrer">
            <Buton tur="ikincil">
              Kaynak kodu GitHub'da
              <ArrowRight className="h-4 w-4" />
            </Buton>
          </a>
        </div>
      </Bolum>

      <Bolum etiket="Sık sorulanlar" baslik="Merak edilenler.">
        <dl className="grid gap-6 sm:grid-cols-2">
          {SORULAR.map((s) => (
            <div key={s.soru}>
              <dt className="font-baslik text-base font-semibold text-murekkep">
                {s.soru}
              </dt>
              <dd className="mt-2 text-sm leading-relaxed text-murekkep-yumusak">
                {s.cevap}
              </dd>
            </div>
          ))}
        </dl>
      </Bolum>

      <section className="border-t border-cizgi py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="mx-auto max-w-2xl font-baslik text-2xl font-semibold tracking-tight text-murekkep sm:text-3xl">
            Bu dönemin programını Dersper kursun.
          </h2>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            {kayitAcik && (
              <Link to="/kayit">
                <Buton className="px-5 py-2.5 text-base">
                  Ücretsiz kurum hesabı açın
                  <ArrowRight className="h-4 w-4" />
                </Buton>
              </Link>
            )}
            <Link to="/giris">
              <Buton tur="ikincil" className="px-4 py-2.5 text-base">
                Giriş yap
              </Buton>
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-cizgi py-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 text-sm text-murekkep-silik">
          <span>Dersper — okullar için açık kaynak ders dağıtım programı</span>
          <a
            href={DEPO}
            target="_blank"
            rel="noreferrer"
            className="transition-colors hover:text-murekkep"
          >
            GitHub · AGPL-3.0
          </a>
        </div>
      </footer>
    </div>
  );
}
