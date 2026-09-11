# Değişiklikler

Dersper'in geliştirme günlüğü. Her değişiklik tek cümleyle, en yeni sürüm en
üstte. Sürüm numarası [semver](https://semver.org/lang/tr/) izler; 1.0
öncesinde ikinci hane özellik, üçüncü hane düzeltme demektir. Uygulamanın
sürümü arayüzde yan menünün altında yazar.

## 0.29.0 — 2026-09-11

- Kısıtlamalar'a "Ders grupları": benzer dersler (Temel Matematik, İleri Matematik, Geometri) bir grupta toplanır ve aynı gruptaki dersler bir şubede arka arkaya gelmez. "Aynı ders arka arkaya gelmesin" kuralıyla birlikte çalışır. Çözücü, yerel arama ve çözümleme raporu grubu tanır; elle taşımayla bozulursa uyarı verir. Bir ders tek grupta olabilir.

## 0.28.0 — 2026-09-11

- Kısıtlamalar'a "Aynı ders arka arkaya gelmesin" kuralı: bir dersin saatleri bir şubede birden fazla öğretmene bölünmüşse bu satırlar da birbirinden ayrılır, aynı gün bitişik saatlere düşmez. Çözücü, sonsuz moddaki yerel arama ve çözümleme raporu kuralı tanır; elle taşımayla bozulursa uyarı verir. Dönem kopyalanırken ayar taşınır.
- Dönemin adını ya da tarihlerini değiştiren istek artık kural ayarlarını (bina geçişi, çakışma ölçütü, şube sırası) sıfırlamıyor.

## 0.27.1 — 2026-09-11

- Ayrı sayfa çıktısında (öğretmenlere/şubelere dağıtılan program) her kayıt tek A4 yatay sayfaya sığıyor: satır yüksekliği ders saati sayısına göre hesaplanır, hücre metni tek satırda kalır, uzun ders adları kısa koduyla yazılır. Gerçek programda 12 saatlik günlerle 25 öğretmen ve 33 şube taşmadan ölçüldü.

## 0.27.0 — 2026-09-11

- Çarşaf görünümünde "Saat sayısı" seçeneği: satır adının yanında yerleşen ders saati yazılır ("Mustafa DİRİM (34)"). Seçim tarayıcıda hatırlanır ve HTML/PDF/Excel çarşaf çıktılarına da yansır.

## 0.26.1 — 2026-09-11

- Bina kuralı esnetilmek zorunda kalınca öğretmen artık gün içinde binalar arasında gidip gelmiyor: önce bir binadaki dersleri biter, sonra öbürüne geçer. Çözücü geçiş sayısını cezalandırır; ikinci ve sonraki geçişler çok daha pahalıdır ve ancak program başka türlü kurulamıyorsa olur. Uyarı da geçiş sırasını ("A → B → A") ve kaç kez değiştiğini yazar.

## 0.26.0 — 2026-09-10

- Şube birleştirme kuralı (Kısıtlamalar sayfası): "9-A ile 9-B, Cumartesi, tam 4 saat" denir; hangi dersin ortak okutulacağını program üretimi seçer. İki şubede aynı öğretmenin verdiği aynı dersler eşlenir, çözücü programın kurulmasını sağlayan dağılımı bulur; ortak saat iki şubeyi ve öğretmeni aynı anda doldurur, iki dersin haftalık saatinden birer düşer, blok desenleri korunur. Ortak saatler programda "9-A + 9-B" olarak görünür; elle taşımada iki şube birden gözetilir; sürüm geçmişi ortak saatleri korur.
- Kural uygulanamıyorsa (eşleşen ders yok, saat fazla, seçilen günlere sığmıyor) üretim başlamadan kesin engel olarak yazılır; öğretmen kapasite denetimleri kuralın düşürebileceği saati hesaba katar.
- Sonsuz moddaki yerel arama motoru birleştirme kuralı varken devre dışı kalır.

## 0.25.0 — 2026-09-10

- Ders programlarında teneffüs ve öğle arası artık satır/sütun değil: ekrandaki ayrı sayfa ve çarşaf görünümlerinde, yayın sayfasında ve HTML/PDF/Excel çıktılarında yalnız ders saatleri var; dersler aralar atlanarak 1'den numaralanıyor.

## 0.24.0 — 2026-09-10

- Yeni kesin ön kontrol (akış tabanlı): bir öğretmenin dersleri şubelerin açık saatlerine, ya da bir şubenin dersleri öğretmenlerinin müsait saatlerine birlikte sığmıyorsa program başlamadan yakalanır; hangi derslerin kaç saat fazla geldiği adıyla yazılır ve "Yapılacak" satırında somut adım verilir (kaç saati başka öğretmene verin / hangi şubelerde kaç ortak saat açın). Basit sayımın (%53 yük) kaçırdığı, üretimi kanıtlı çözümsüz bırakan asıl tıkanma buydu.
- Engel bulgularında "Yapılacak" satırı gösteriliyor; yapay zeka özeti de bu adımı alıyor.
- Canlı üretimdeki "çözücü kanıtladı" uyarısı bulguların tablonun altındaki bölümde olduğunu söylüyor.

## 0.23.2 — 2026-09-10

- Program sayfasında tablo en üstte; "Program neden tamamlanamadı" ve "Yapay zeka yorumu" kartları tablonun altına indi ve katlanır, kapalı başlıyor (başlıkta "5 saat yerleşemedi" özeti). Üstte yalnızca canlı üretim bilgisi kalıyor.

## 0.23.1 — 2026-09-10

- Program sayfasındaki Uyarılar kartı katlanır ve kapalı başlar; başlıkta "3 uyarı, 1 gizli" gibi özet görünür.

## 0.23.0 — 2026-09-10

- Yapay zeka açıklaması kısaldı ve hedefe odaklandı (en fazla 120 kelime): ana sebep tek cümle, ardından "Denenmiş çözümler" (çözücünün arka planda sınayıp tek başına yettiğini doğruladığı değişiklikler, öyle de etiketlenir) ve en fazla üç "denenmedi" işaretli somut öneri; modele tam rapor yerine kısaltılmış özet gidiyor.

## 0.22.7 — 2026-09-10

- Çelişki ve sıkışıklık önerileri öğretmenin gerçek kısıtlarına göre yazılıyor: kapalı saati olmayan öğretmene "müsaitlik matrisinde saat açın", gün sınırı olmayana "gün sınırını yükseltin" denmiyor.

## 0.22.6 — 2026-09-10

- Sıkışıklık ipuçlarında şubeler listelenmiyor ("7/A: 14 saat yükü, 14 açık saati var (%100)" gibi satırlar kalktı); şube programı tam dolduğu için bu oran bilgi taşımıyordu, yalnız öğretmenler kaldı.

## 0.22.5 — 2026-09-10

- Birleşik derste ortak şubenin kapalı saatleri artık diğer şubenin kapasitesine yazılmıyor; 11/EA-1 gibi tam sığan bir şube "haftaya sığmıyor" diye yanlış engel almıyor.

## 0.22.4 — 2026-09-10

- Şube/öğretmen kapasite tanısı yalnızca ızgaradaki hücrelerin "uygun değil" kayıtlarını sayıyor; teneffüse çevrilmiş, pasif güne ya da kısaltılmış güne ait hayalet hücreler artık "haftaya sığmıyor" diye yanlış engel üretmiyor ve gerçek çelişki çözümlemesini gizlemiyor.

## 0.22.3 — 2026-09-03

- Dersler ve Şubeler listelerinde haftalık ders yükü sütunu (birleşik dersler her üye şubeye sayılır).

## 0.22.2 — 2026-09-03

- Öğretmen listesinde haftalık ders yükü sütunu.

## 0.22.1 — 2026-09-03

- Çelişki raporunda şube için "boşluk payı yok" gerekçesi kaldırıldı (şube programı tam dolu olur, bu olağandır); işaretlenen şubede dersler tek tek sınanıp hangi ders ve öğretmenin çıkınca programın kurulduğu, öğretmenin yük/açık saatiyle birlikte yazılıyor; şubenin hiçbir öğretmeninin müsait olmadığı saatler de listeleniyor.

## 0.22.0 — 2026-09-03

- Sonsuz moda beşinci motor: yerel arama (benzetimli tavlama). CP-SAT'ten bağımsız, dış paket kullanmayan bu motor en iyi yerleşimden başlayıp blokları taşıyıp takas ederek eksik saati ve gün sınırı / bina cezalarını düşürmeye çalışır; sert kurallar (çakışma, müsaitlik, blok bütünlüğü, günlük sınır, bitişik blok yasağı, kilit) aynen korunur.

## 0.21.0 — 2026-09-03

- Sonsuz mod: program kurulamasa bile dört farklı arama stratejisi (otomatik portföy, sabit arama, ipuçlu, doğrusal gevşetmeli) sırayla döndürülerek siz durdurana kadar denenir; iyileşen deneme ızgaraya hemen yazılır.
- Her çözücü denemesi sürüm geçmişine yazılıyor ("Deneme 7 · İpuçlu — 440/447") ve incelenip geri yüklenebiliyor; canlı izlemede strateji ve deneme günlüğü (süre, sonuç, yerleşen) görünüyor.

## 0.20.2 — 2026-09-03

- Çelişki raporunda kaynak satırları gerekçesini söylüyor: "24 saat yük 24 açık saate tam sığıyor, boşluk payı yok — kısıtları kaldırılınca program kuruluyor"; başlık da "her biri tek tek sınandı" diye netleşti.

## 0.20.1 — 2026-09-03

- Büyük okullarda "program neden kurulamadı" önerileri boş kalıyordu: çelişki araması artık modele göre süre alıyor ve büyük modelde hızlı kanıtla silme yöntemine geçiyor (hangi öğretmenin/şubenin kısıtları çelişkiye katılıyor, tek başına hangisi yeter); süre yetmeyen sınamalar "bilinmiyor" diye işaretleniyor, kesin çelişki çıkmazsa en sıkışık kaynaklar listeleniyor.
- Sert ve esnek model çözümsüzlüğü kanıtladıysa üretim döngüsü artık saatlerce dönmüyor; en iyi gevşek yerleşimi yazıp "çözümsüz" olarak bitiyor.

## 0.20.0 — 2026-09-03

- Kısıtlamalar ekranı: programı bağlayan kurallar tek yerde toplanıyor; bina kuralı Binalar'dan, çakışma ölçütü Zaman Izgarası'ndan buraya taşındı, eski yerlerinde yönlendirme bırakıldı.

## 0.19.1 — 2026-09-03

- Ders atamasında ders seçilince öğretmen listesi o dersin branş öğretmenlerini (branşı uyan ya da dersi zaten okutan) üstte, diğerlerini altta, ikisini de ada göre gösteriyor; yeni kayıtta ilk branş öğretmeni seçili gelir.

## 0.19.0 — 2026-09-03

- Öğretmen müsaitliği başka öğretmenlere toplu kopyalanabiliyor: müsaitlik penceresinde "Başka öğretmenlere kopyala", hedefleri seçip tek adımda uygular (şubelerdeki gibi).

## 0.18.1 — 2026-09-03

- Ders atamasında şube seçimi sadeleşti: eklenen şube etiket olarak seçili gelir, ortak ders için "+ Şube ekle" ile aranabilir listeden başka şube katılır.

## 0.18.0 — 2026-09-03

- Dönem kopyalama: Dönemler sayfasından bir dönemin tamamı — zaman ızgarası, binalar, öğretmenler ve şubeler (müsaitlikleriyle), dersler, ders atamaları (birleşikler dahil) ve dönem ayarları — tek adımda yeni döneme kopyalanıyor; programlar kopyalanmıyor.

## 0.17.0 — 2026-09-03

- Şube sırası kurumun seçimine bırakıldı: ada göre doğal sıra (9-A, 9-B, 10-A) ya da Şubeler sayfasında sürükleyip kaydedilen elle sıra; aynı sıra listelerde, atama ve program şeritlerinde, çarşafta, yayın sayfasında ve çıktılarda geçerli.

## 0.16.0 — 2026-09-03

- Ders programında sağ tık menüsü (dokunmatikte tek dokunuş): "Taşı…" hedef saati listeden seçtiriyor, ayrıca kilitle / kilidi aç ve rafa al; raftaki blokta "Yerleştir…" — küçük ekranda sürüklemenin yerine geçer.

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
