"""Yapay zeka katmanı.

Kurum kendi API anahtarını ve uç noktasını Ayarlar'dan girer. OpenAI SDK
kullanılır; `base_url` değiştirilebildiği için OpenAI, Ollama, OpenRouter,
LM Studio ve OpenAI uyumlu diğer servisler aynı kodla çalışır.

v1'deki tek görev: program yerleşmediğinde çözümsüzlük raporunu kısa, hedefe
odaklı Türkçeye çevirmek. Rapordaki çözüm adayları çözücü tarafından arka
planda sınanmıştır; model hangisinin denenip yettiğini söyler, kendisi sınamaz. Yapay zeka kapalıyken uygulama tüm işlevleriyle çalışmaya devam eder.
"""
from __future__ import annotations

import json

from openai import OpenAI

from app.crypto import decrypt
from app.models import AiSettings

SISTEM_MESAJI = """Sen bir okulun ders programı yazılımının yardımcısısın. Sana, programın
neden kurulamadığını anlatan kısa bir teknik özet verilecek. Okul yönetimine
hitap eden, hedefe odaklı, kısa bir Türkçe metin yaz.

Kurallar:
- Teknik terim yok ("kısıt", "çözücü", "model" yasak). Selamlama, giriş ve
  kapanış cümlesi yok. Gerekçe anlatma; ne yapılacağını söyle.
- İlk satır: tıkanmanın ana sebebi, tek cümle.
- "Denenmiş çözümler" başlığı: özetteki `denenmis_cozumler` listesi. Her madde
  tek cümle, sonunda "— arka planda denendi, bu değişiklik tek başına yetiyor."
  Liste boşsa bu başlığı yazma.
- "Öneriler" başlığı: en fazla 3 somut, sayısal adım (kim, kaç saat, hangi ders).
  Her maddenin sonuna "— denenmedi." ekle. Denenmiş çözümleri tekrarlama.
  `yetmeyenler` listesindekileri tek başına önerme.
- Sadece özetteki bilgiyi kullan; ad, sayı, ders uydurma.
- Markdown başlık ve madde işareti kullan. En fazla 120 kelime.
"""


class AiKapali(Exception):
    """Yapay zeka ayarlanmamış ya da kapalı."""


def _istemci(api_key: str, base_url: str | None) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url or None)


def modelleri_getir(
    ayar: AiSettings | None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> list[str]:
    """Sağlayıcının models ucundan kullanılabilir model adlarını çeker.

    Henüz kaydedilmemiş bilgilerle de çalışır: `api_key` verilmezse kayıtlı
    anahtar kullanılır. Liste dönüyorsa adres ve anahtar doğrulanmış olur.
    """
    anahtar = (api_key or "").strip()
    if not anahtar:
        if ayar is None or not ayar.api_key_encrypted:
            raise AiKapali("Önce API anahtarınızı girin.")
        anahtar = decrypt(ayar.api_key_encrypted)
        if not anahtar:
            raise AiKapali("Kayıtlı API anahtarı okunamadı. Anahtarı yeniden girin.")

    adres = base_url if base_url is not None else (ayar.base_url if ayar else None)
    yanit = _istemci(anahtar, (adres or "").strip() or None).models.list()
    return sorted({m.id for m in yanit.data if getattr(m, "id", None)})


def istemci_olustur(ayar: AiSettings | None) -> tuple[OpenAI, str]:
    if ayar is None or not ayar.enabled or not ayar.api_key_encrypted:
        raise AiKapali(
            "Yapay zeka kapalı. Ayarlar > Yapay Zeka bölümünden API anahtarınızı girin."
        )
    api_key = decrypt(ayar.api_key_encrypted)
    if not api_key:
        raise AiKapali("Kayıtlı API anahtarı okunamadı. Anahtarı yeniden girin.")
    return _istemci(api_key, ayar.base_url), ayar.model


def baglanti_testi(ayar: AiSettings | None) -> tuple[bool, str]:
    """Ayarların gerçekten çalıştığını doğrular."""
    try:
        client, model = istemci_olustur(ayar)
    except AiKapali as e:
        return False, str(e)
    try:
        yanit = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Sadece 'tamam' yaz."}],
            max_tokens=10,
        )
        icerik = (yanit.choices[0].message.content or "").strip()
        return True, f"Bağlantı başarılı. Model yanıtı: {icerik or '(boş)'}"
    except Exception as e:  # sağlayıcıya özgü hataları kullanıcıya taşı
        return False, f"Bağlantı kurulamadı: {e}"


def rapor_ozeti(rapor: dict, en_fazla: int = 5) -> dict:
    """Yapay zekaya giden kısaltılmış rapor.

    Tam rapor gürültülüdür (özet sayılar, süre, her yerleşmeyen ders). Modele
    yalnızca karar için gerekeni veririz: kesin engeller, arka planda sınanmış
    çözümler (`tek_basina_yeterli`), sınanıp yetmeyenler, sıkışık öğretmenler
    ve en çok saati boş kalan dersler. Kısa girdi, kısa ve doğru çıktı verir.
    """
    bulgular = rapor.get("bulgular", [])
    celiskiler = rapor.get("celiskiler", [])

    def madde(c: dict) -> dict:
        return {"sorun": c.get("metin", ""), "yapilacak": c.get("oneri", "")}

    return {
        "kesin_engeller": [
            {"baslik": b.get("baslik", ""), "detay": b.get("detay", ""),
             "yapilacak": b.get("oneri", "")}
            for b in bulgular if b.get("onem") == "engel"
        ][:en_fazla],
        "denenmis_cozumler": [
            madde(c) for c in celiskiler if c.get("tek_basina_yeterli") is True
        ][:en_fazla],
        "yetmeyenler": [
            c.get("metin", "") for c in celiskiler
            if c.get("tek_basina_yeterli") is False
        ][:en_fazla],
        "denenmemis_ipuclari": [
            madde(c) for c in celiskiler if c.get("tek_basina_yeterli") is None
        ][:en_fazla] + [
            {"sorun": s.get("metin", ""), "yapilacak": s.get("oneri", "")}
            for s in rapor.get("sikisiklik", [])
        ][:3],
        "yerlesmeyen_dersler": rapor.get("yerlesmeyenler", [])[:en_fazla],
        "yerlesmeyen_toplam_saat": rapor.get("ozet", {}).get("yerlesmeyen_toplam"),
    }


def cozumsuzluk_acikla(ayar: AiSettings | None, rapor: dict) -> str:
    """Teknik raporu okul yönetimine hitap eden kısa Türkçe metne çevirir."""
    client, model = istemci_olustur(ayar)
    yanit = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SISTEM_MESAJI},
            {
                "role": "user",
                "content": "Ders programı tıkanma özeti:\n\n"
                + json.dumps(rapor_ozeti(rapor), ensure_ascii=False, indent=2),
            },
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return (yanit.choices[0].message.content or "").strip()
