"""Yapay zeka katmanı.

Kurum kendi API anahtarını ve uç noktasını Ayarlar'dan girer. OpenAI SDK
kullanılır; `base_url` değiştirilebildiği için OpenAI, Ollama, OpenRouter,
LM Studio ve OpenAI uyumlu diğer servisler aynı kodla çalışır.

v1'deki tek görev: program yerleşmediğinde çözümsüzlük raporunu sade Türkçeye
çevirmek. Yapay zeka kapalıyken uygulama tüm işlevleriyle çalışmaya devam eder.
"""
from __future__ import annotations

import json

from openai import OpenAI

from app.crypto import decrypt
from app.models import AiSettings

SISTEM_MESAJI = """Sen bir okulun ders programı hazırlama yazılımının yardımcısısın.
Sana, otomatik ders programı üretiminin neden tamamlanamadığını anlatan
yapılandırılmış bir teknik rapor verilecek.

Görevin, okul müdürüne veya müdür yardımcısına hitap eden sade bir Türkçe
açıklama yazmak. Kurallar:
- Teknik terim kullanma. "kısıt", "çözücü", "model", "değişken" gibi kelimeler yasak.
- Doğrudan konuya gir. Selamlama ve kapanış cümlesi yazma.
- Önce tek cümlelik özet ver: programın tıkandığı ana sebep ne.
- Sonra "Tıkanmanın sebepleri" başlığı altında maddeler halinde açıkla.
- Sonra "Ne yapabilirsiniz" başlığı altında somut, uygulanabilir öneriler ver.
  Öneriler sayısal olsun: hangi öğretmenin kaç saatini açması, hangi dersin
  günlük sınırının kaça çıkarılması gerektiği gibi.
- Sadece raporda geçen bilgileri kullan. Veri uydurma.
- Markdown başlık ve madde işaretleri kullan. En fazla 350 kelime.
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


def cozumsuzluk_acikla(ayar: AiSettings | None, rapor: dict) -> str:
    """Teknik raporu okul yönetimine hitap eden Türkçe metne çevirir."""
    client, model = istemci_olustur(ayar)
    yanit = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SISTEM_MESAJI},
            {
                "role": "user",
                "content": "Ders programı üretim raporu:\n\n"
                + json.dumps(rapor, ensure_ascii=False, indent=2),
            },
        ],
        temperature=0.2,
        max_tokens=900,
    )
    return (yanit.choices[0].message.content or "").strip()
