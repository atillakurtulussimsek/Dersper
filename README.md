# Dersper

Okullar ve kurslar için ücretsiz, açık kaynaklı **haftalık ders dağıtım (ders programı) yazılımı**.
Web tabanlı, kendi sunucunuza kurulur, verileriniz sizde kalır.
Çok kurumlu: her kurum kendi kullanıcıları, dönemleri ve programlarıyla yalıtılmıştır.

aSc TimeTables, ProgMatik, Bilsa ve Yabil gibi ücretli programlara özgür bir alternatif.

## Neler yapar

- **Dönemler**: her dönem kendi zaman ızgarası, kadrosu, dersleri, şubeleri ve programlarıyla bağımsız; geçmiş dönemden seçerek kayıt aktarma
- Öğretmen, ders, şube ve ders atamaları (kısa kod ve renk otomatik önerilir)
- Bir derse birden fazla öğretmen: saatler öğretmenler arasında bölünebilir
- Müfredatı başka şubelere kopyalama (tek ders ya da şubenin tamamı)
- Güne göre değişken ders saati / zil düzeni
- Öğretmen müsaitlik matrisi
- Şube ders saati kısıtları (sabahçı / akşamcı şubeler), başka şubelere kopyalanabilir
- Kısıt tabanlı otomatik program üretimi (Google OR-Tools CP-SAT)
- **Arka planda üretim**: tam yerleşim sağlanana kadar denemeye devam eder; ekranı kapatsanız da sürer. Deneme sayısı, geçen süre ve en iyi yerleşim canlı izlenir, istenildiğinde durdurulur
- Serbest ders dağılımı (5 saatlik ders 2+2+1, 1+1+2+1 ya da 3+2 olarak), günlük ders tekrar sınırı, çakışma önleme
- Gerektiğinde günlük sınırın esnetilmesi: aynı ders gün içinde birden çok kez, aralarına başka dersler konarak yerleşir; esnetilen yerler **Uyarılar** bölümünde listelenir ve isteğe bağlı düzeltilir
- Program yerleşmediğinde **yapay zeka destekli, sade Türkçe açıklama**: neyin tıkadığı, hangi kısıtın gevşetilmesi gerektiği
- Çıktılar: sınıf/öğretmen bazında ayrı sayfalar ya da tek sayfalık **çarşaf liste**; PDF, Excel ve yazdırma
- Halka açık salt-okunur görünüm

Yapay zeka isteğe bağlıdır. Kendi API anahtarınızı Ayarlar'dan girersiniz; kapalıyken program tüm işlevleriyle çalışır.

## Teknoloji

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy · Alembic |
| Çözücü | Google OR-Tools (CP-SAT) |
| Frontend | React · TypeScript · Vite · Tailwind CSS |
| Veritabanı | MySQL 8 |
| Yapay zeka | OpenAI SDK (özel `base_url` desteğiyle: OpenAI, Ollama, OpenRouter, uyumlu her servis). Model listesi sağlayıcıdan çekilir. |

## Kurulum

Gereksinimler: Python 3.12+, Node.js 20+, erişilebilir bir MySQL 8 veritabanı.

```bash
git clone https://github.com/atillakurtulussimsek/Dersper.git
cd Dersper
cp .env.example .env      # veritabanı bilgilerinizi girin
```

Backend bağımlılıkları:

```bash
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Frontend bağımlılıkları:

```bash
cd frontend && npm install
```

Sonra kök dizinden:

```bash
./run.sh
```

`run.sh` backend'i ve frontend'i birlikte başlatır. Arayüz: http://localhost:5173

İlk açılışta kurum kaydı ekranı karşılar: kurumunuzu, ilk hesabınızı ve ilk döneminizi oluşturur.

Herkese açık kayıt `.env` içindeki `ALLOW_REGISTRATION` ile kapatılabilir. Kapalıyken bile,
sistemde hiç kurum yoksa ilk kayda izin verilir; sonraki hesapları kurum içinden
**Kullanıcılar** bölümünden açarsınız. Bir hesap yalnızca bir kuruma bağlanır.

Silme her yerde yumuşaktır: kayıtlar gizlenir, veritabanından kaldırılmaz.

## Sunucuya kurulum (Docker)

Dokploy, Coolify ya da düz Docker ile:

```bash
cp .env.example .env      # DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY doldurun
docker compose up -d --build
```

Tek servis ayağa kalkar: imaj arayüzü derler, FastAPI hem `/api`'yi hem
derlenmiş arayüzü aynı porttan sunar. Açılışta veritabanı şeması güncellenir.
PDF için gereken pango/cairo imajda gelir.

Ayrı bir web sunucusu, konteynerler arası ağ ve ikinci alan adı gerekmez;
arayüz ile API aynı kökeni paylaştığı için CORS ayarı da gerekmez.

`.env` dosyasındaki değişkenlerin tamamı konteynere olduğu gibi aktarılır.
Doldurmanız gereken üç değer var: `DATABASE_URL`, `SECRET_KEY`, `ENCRYPTION_KEY`.
Gerisi olduğu gibi bırakılabilir.

Veritabanı harici bir MySQL 8 sunucusudur — compose içinde veritabanı servisi
yoktur, `DATABASE_URL` ile kendi sunucunuzu gösterirsiniz.

`docker-compose.yml` ana makineye **port bağlamaz**. Dokploy, Coolify gibi
ortamlar konteynere kendi ters vekilleriyle ulaşır. Panelden alan adınızı `app`
servisinin **8000** numaralı portuna yönlendirin.

Ters vekili olmayan düz bir sunucuda çalıştıracaksanız port yayımlayan ek
dosyayı kullanın:

```bash
docker compose -f docker-compose.yml -f docker-compose.standalone.yml up -d
```

Bu durumda uygulama `.env` içindeki `WEB_PORT` portundan (varsayılan `8080`)
yayınlanır.

Sorun giderme:

| Adres | Söylediği |
|---|---|
| `/api/health` | Uygulama süreci ayakta mı |
| `/api/health/db` | Veritabanına ulaşılabiliyor mu (ulaşılamıyorsa 503 ve sebebi) |

> **Dokploy kullanıyorsanız:** build yöntemi olarak **Docker Compose**'u seçin.
> Nixpacks bu depoda çalışmaz: kökte iki ayrı çalışma ortamı (Python ve Node)
> vardır ve WeasyPrint sistem kütüphaneleri ister.
>
> Alan adı ayarında servis olarak `app`, port olarak `8000` girin.

## Lisans

[GNU Affero General Public License v3.0](LICENSE) — özgür yazılım. Değiştirip
sunucunuzda çalıştırırsanız, kaynağı kullanıcılarınıza açmakla yükümlüsünüz.
