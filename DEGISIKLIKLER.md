# Değişiklikler

Dersper'in geliştirme günlüğü. Her değişiklik tek cümleyle, en yeni sürüm en
üstte. Sürüm numarası [semver](https://semver.org/lang/tr/) izler; 1.0
öncesinde ikinci hane özellik, üçüncü hane düzeltme demektir. Uygulamanın
sürümü arayüzde yan menünün altında yazar.

## 0.15.0 — 2026-09-03

- Sürüm farkı: sürüm geçmişinde "Fark" ile iki sürüm arasında hangi dersin nereden nereye taşındığı, hangisinin çıktığı ya da eklendiği ve kilit değişiklikleri listeleniyor; yön çevrilebiliyor.

## 0.14.1 — 2026-09-03

- Ortak ders hücrede belli oluyor: ders adının yanında (çarşafta köşede) küçük bir kişiler simgesi, alt satırda ve ipucunda birlikte işleyen şubeler.

## 0.14.0 — 2026-09-03

- Birleşik dersler: ders atamasında birden fazla şube seçilirse ders o şubelere birlikte işlenir — tek öğretmen, tek saat; her şubenin programında görünür, çözücü ve elle düzenleme şubelerin hepsini o saatte dolu sayar.
- Bir şube aynı dersi hem birleşik hem ayrı alabilir (2 saat ortak, 1 saat kendi); "bir şubede bir ders bir kez" kuralı şube bileşimine göre işler.

## 0.13.0 — 2026-09-02

- Çakışma ölçütü kurumun seçimine bırakıldı: ızgaranın satırı (1., 2., 3. ders) ya da gerçek saat aralığı (1. ders 09:00–09:40); seçim hem program üretimini hem elle düzenlemeyi bağlar.
- Zaman ızgarası, saatleri üst üste binen, sırası ters ya da yarım girilmiş satırları uyarıyor.

## 0.12.2 — 2026-09-01

- Ders programı ekranı sadeleşti: sürüm geçmişi, geçmiş çalıştırmalar ve yayın bölümleri katlanır hâle geldi, özet sayımlar araç çubuğuna taşındı, kullanım notları tek satıra indi.

## 0.12.1 — 2026-09-01

- 0.12.0'daki Metronic teması geri alındı: tema tescilli olduğu için herkese açık depoda dağıtılamıyor, arayüz kendi tasarımına döndü.

## 0.12.0 — 2026-09-01

- Arayüzün tamamı Metronic 8 temasına taşındı (0.12.1'de geri alındı).

## 0.11.0 — 2026-09-01

- Program kurulamadığında hangi kısıtların birbiriyle çeliştiği ve hangisini tek başına değiştirmenin yeteceği yazılıyor.

## 0.10.0 — 2026-08-31

- Bina modülü eklendi: şubeler binalara bağlanıyor ve istenirse bir öğretmenin bir günkü dersleri tek binada toplanıyor.
- Program üretimine öğretmen boşluğu tercihi eklendi — boşluklu, ideal ya da sıkı.

## 0.9.0 — 2026-08-31

Sürüm numarası bu noktada verildi; aşağıdakiler 27 Ağustos'tan bu yana yapılan
geliştirmelerin özetidir.

### Program üretimi
- Ders programı OR-Tools CP-SAT ile otomatik üretiliyor.
- Üretim arka planda sürüyor; ilerleme canlı izleniyor ve istendiğinde durduruluyor.
- Program kurulamadığında nedeni sade Türkçeyle anlatan tanı raporu üretiliyor.
- Haftalık saatin gün içindeki dağılımı "2+2+1" gibi desenlerle belirleniyor.
- Günlük ders tekrar sınırı gerektiğinde esnetiliyor ve aşım uyarı olarak listeleniyor.
- Öğretmenin haftada kaç gün okulda olacağı sınırlanabiliyor; yarım gün de kabul ediliyor.
- Yapay zekâ (kendi anahtarınızla) tanı raporunu yorumluyor.

### Elle düzenleme
- Ders programı sürükle-bırak ile düzenleniyor; blok bütün taşınıyor.
- Dolu bir hücreye bırakmak iki dersi yer değiştiriyor.
- Ders ızgaradan alınıp bekleyenler rafına konabiliyor ve oradan geri yerleştirilebiliyor.
- Sürükleme sırasında dersin konabileceği saatler işaretleniyor, konamayanların nedeni yazıyor.
- Her değişiklik sürüm olarak saklanıyor; istenen sürüme dönülebiliyor, geri ve ileri alınabiliyor.
- Kilitlenen dersler yeniden üretimde yerinde kalıyor.

### Tanımlar
- Öğretmen, ders, şube ve ders atamaları yönetiliyor.
- Ders atamaları hem şube hem öğretmen tarafından görülüp girilebiliyor.
- Zaman ızgarası dönem başına tanımlanıyor; günler farklı uzunlukta olabiliyor.
- Izgara satırları sürüklenerek sıralanıyor, öğle arası işaretlenebiliyor.
- Öğretmen ve şube müsaitliği haftalık matriste işaretleniyor.
- Bir derse birden fazla öğretmen atanabiliyor.
- Ders atamaları ve müsaitlik tabloları başka şubelere kopyalanabiliyor.
- Ders ve öğretmen kısa kodları addan otomatik türetiliyor.
- Tanımlar döneme ait; geçmiş dönemden aktarma yapılabiliyor.
- Silme her yerde yumuşak: kayıt gizleniyor, veritabanından kaldırılmıyor.

### Görüntüleme ve çıktı
- Program şube ya da öğretmen bakışıyla görüntüleniyor.
- Çarşaf görünümü hem ekranda hem çıktıda tüm şubeleri tek tabloda gösteriyor.
- PDF, Excel ve yazdırma çıktıları alınabiliyor.
- Program herkese açık bir bağlantıyla girişsiz paylaşılabiliyor.
- Özet ekranı doluluk oranını yalnızca ders konulabilen saatler üzerinden hesaplıyor.
- Arayüz açık ve koyu temayı destekliyor.

### Kurulum ve kurum
- Kurumlar kendi hesabını açıp kendi verisiyle çalışıyor; kurumlar birbirinden yalıtık.
- Kurum içinde birden fazla kullanıcı tanımlanabiliyor.
- Uygulama tek konteyner olarak dağıtılıyor; arayüzü FastAPI sunuyor.
- Sürüm numarası yan menüde gösteriliyor.
