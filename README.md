# Dersper

Okullar ve kurslar için ücretsiz, açık kaynaklı **haftalık ders dağıtım (ders programı) yazılımı**.
Web tabanlı, kendi sunucunuza kurulur, verileriniz sizde kalır.

aSc TimeTables, ProgMatik, Bilsa ve Yabil gibi ücretli programlara özgür bir alternatif.

## Neler yapar

- Öğretmen, ders, şube ve müfredat tanımları
- Güne göre değişken ders saati / zil düzeni
- Öğretmen müsaitlik matrisi
- Şube ders saati kısıtları (sabahçı / akşamcı şubeler)
- Kısıt tabanlı otomatik program üretimi (Google OR-Tools CP-SAT)
- Blok (çift) ders, günlük ders tekrar sınırı, çakışma önleme
- Program yerleşmediğinde **yapay zeka destekli, sade Türkçe açıklama**: neyin tıkadığı, hangi kısıtın gevşetilmesi gerektiği
- Sınıf / öğretmen bazında PDF ve Excel çıktısı, halka açık salt-okunur görünüm

Yapay zeka isteğe bağlıdır. Kendi API anahtarınızı Ayarlar'dan girersiniz; kapalıyken program tüm işlevleriyle çalışır.

## Teknoloji

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy · Alembic |
| Çözücü | Google OR-Tools (CP-SAT) |
| Frontend | React · TypeScript · Vite · Tailwind CSS |
| Veritabanı | MySQL 8 |
| Yapay zeka | OpenAI SDK (özel `base_url` desteğiyle: OpenAI, Ollama, OpenRouter, uyumlu her servis) |

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

İlk açılışta kurum bilgilerinizi ve yönetici hesabınızı oluşturan bir kurulum sihirbazı karşılar.

## Lisans

[GNU Affero General Public License v3.0](LICENSE) — özgür yazılım. Değiştirip
sunucunuzda çalıştırırsanız, kaynağı kullanıcılarınıza açmakla yükümlüsünüz.
