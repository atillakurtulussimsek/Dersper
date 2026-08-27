/** Kurum bilgileri ve yapay zeka sağlayıcı ayarları. */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Sparkles } from "lucide-react";

import { Alan, Buton, Girdi, Kart, Secim, Uyari, Yukleniyor } from "../components/ui";
import { del, get, put } from "../lib/api";
import type { Kurum, KurumTipi, YapayZekaAyarlari } from "../lib/types";

const HAZIR_UCLAR = [
  { ad: "OpenAI", url: "", model: "gpt-4o-mini" },
  { ad: "OpenRouter", url: "https://openrouter.ai/api/v1", model: "openai/gpt-4o-mini" },
  { ad: "Ollama (yerel)", url: "http://localhost:11434/v1", model: "llama3.1" },
  { ad: "Google Gemini", url: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.0-flash" },
];

export default function Ayarlar() {
  const qc = useQueryClient();
  const kurum = useQuery({ queryKey: ["kurum"], queryFn: () => get<Kurum>("/institution") });
  const yz = useQuery({
    queryKey: ["yz-ayarlar"],
    queryFn: () => get<YapayZekaAyarlari>("/ai/settings"),
  });

  const [kurumForm, setKurumForm] = useState({ name: "", type: "k12" as KurumTipi, address: "" });
  const [yzForm, setYzForm] = useState({
    enabled: false,
    base_url: "",
    model: "gpt-4o-mini",
    api_key: "",
  });

  useEffect(() => {
    if (kurum.data)
      setKurumForm({
        name: kurum.data.name,
        type: kurum.data.type,
        address: kurum.data.address ?? "",
      });
  }, [kurum.data]);

  useEffect(() => {
    if (yz.data)
      setYzForm({
        enabled: yz.data.enabled,
        base_url: yz.data.base_url ?? "",
        model: yz.data.model,
        api_key: "",
      });
  }, [yz.data]);

  const kurumKaydet = useMutation({
    mutationFn: () =>
      put<Kurum>("/institution", { ...kurumForm, address: kurumForm.address || null }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kurum"] }),
  });

  const yzKaydet = useMutation({
    mutationFn: () =>
      put<YapayZekaAyarlari>("/ai/settings", {
        enabled: yzForm.enabled,
        base_url: yzForm.base_url || null,
        model: yzForm.model,
        api_key: yzForm.api_key || null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["yz-ayarlar"] }),
  });

  const yzTest = useMutation({
    mutationFn: () => get<{ ok: boolean; message: string }>("/ai/test"),
  });

  const anahtarSil = useMutation({
    mutationFn: () => del("/ai/settings/key"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["yz-ayarlar"] }),
  });

  if (kurum.isLoading || yz.isLoading) return <Yukleniyor />;

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Ayarlar</h1>
        <p className="text-sm text-slate-500">Kurum bilgileri ve yapay zeka bağlantısı.</p>
      </header>

      <Kart baslik="Kurum bilgileri">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            kurumKaydet.mutate();
          }}
        >
          <Alan etiket="Kurum adı">
            <Girdi
              required
              value={kurumForm.name}
              onChange={(e) => setKurumForm({ ...kurumForm, name: e.target.value })}
            />
          </Alan>
          <Alan etiket="Kurum tipi">
            <Secim
              value={kurumForm.type}
              onChange={(e) => setKurumForm({ ...kurumForm, type: e.target.value as KurumTipi })}
            >
              <option value="k12">Okul (ilkokul / ortaokul / lise)</option>
              <option value="kurs">Kurs / dershane / dil okulu</option>
            </Secim>
          </Alan>
          <Alan etiket="Adres">
            <Girdi
              value={kurumForm.address}
              onChange={(e) => setKurumForm({ ...kurumForm, address: e.target.value })}
            />
          </Alan>
          {kurumKaydet.error && <Uyari tur="hata">{(kurumKaydet.error as Error).message}</Uyari>}
          {kurumKaydet.isSuccess && <Uyari tur="basari">Kurum bilgileri kaydedildi.</Uyari>}
          <Buton type="submit" yukleniyor={kurumKaydet.isPending}>
            Kaydet
          </Buton>
        </form>
      </Kart>

      <Kart
        baslik="Yapay zeka"
        aciklama="Kendi API anahtarınızı kullanırsınız; anahtar şifrelenerek saklanır ve yalnızca sizin sunucunuzda kalır."
        sag={<Sparkles className="h-4 w-4 text-slate-400" />}
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            yzKaydet.mutate();
          }}
        >
          <Uyari>
            Yapay zeka isteğe bağlıdır. Kapalıyken program üretimi ve tüm diğer işlevler
            aynı şekilde çalışır; yalnızca tıkanma anındaki sade Türkçe açıklama devre
            dışı kalır.
          </Uyari>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={yzForm.enabled}
              onChange={(e) => setYzForm({ ...yzForm, enabled: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300"
            />
            Yapay zeka desteğini aç
          </label>

          <Alan etiket="Hazır sağlayıcılar" ipucu="Seçince adres ve model alanlarını doldurur.">
            <div className="flex flex-wrap gap-2">
              {HAZIR_UCLAR.map((u) => (
                <button
                  key={u.ad}
                  type="button"
                  onClick={() => setYzForm({ ...yzForm, base_url: u.url, model: u.model })}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                >
                  {u.ad}
                </button>
              ))}
            </div>
          </Alan>

          <Alan
            etiket="API adresi (base URL)"
            ipucu="OpenAI kullanıyorsanız boş bırakın. OpenAI uyumlu her servis çalışır."
          >
            <Girdi
              value={yzForm.base_url}
              onChange={(e) => setYzForm({ ...yzForm, base_url: e.target.value })}
              placeholder="https://api.openai.com/v1"
            />
          </Alan>

          <Alan etiket="Model">
            <Girdi
              required
              value={yzForm.model}
              onChange={(e) => setYzForm({ ...yzForm, model: e.target.value })}
            />
          </Alan>

          <Alan
            etiket="API anahtarı"
            ipucu={
              yz.data?.has_api_key
                ? `Kayıtlı anahtar: ${yz.data.api_key_masked}. Değiştirmek istemiyorsanız boş bırakın.`
                : "Henüz anahtar kaydedilmemiş."
            }
          >
            <Girdi
              type="password"
              value={yzForm.api_key}
              onChange={(e) => setYzForm({ ...yzForm, api_key: e.target.value })}
              placeholder="sk-…"
              autoComplete="off"
            />
          </Alan>

          {yzKaydet.error && <Uyari tur="hata">{(yzKaydet.error as Error).message}</Uyari>}
          {yzKaydet.isSuccess && <Uyari tur="basari">Yapay zeka ayarları kaydedildi.</Uyari>}
          {yzTest.data && (
            <Uyari tur={yzTest.data.ok ? "basari" : "hata"}>{yzTest.data.message}</Uyari>
          )}

          <div className="flex flex-wrap gap-2">
            <Buton type="submit" yukleniyor={yzKaydet.isPending}>
              Kaydet
            </Buton>
            <Buton
              tur="ikincil"
              type="button"
              onClick={() => yzTest.mutate()}
              yukleniyor={yzTest.isPending}
            >
              <KeyRound className="h-4 w-4" /> Bağlantıyı test et
            </Buton>
            {yz.data?.has_api_key && (
              <Buton
                tur="tehlike"
                type="button"
                onClick={() => {
                  if (confirm("Kayıtlı API anahtarı silinsin mi?")) anahtarSil.mutate();
                }}
                yukleniyor={anahtarSil.isPending}
              >
                Anahtarı sil
              </Buton>
            )}
          </div>
        </form>
      </Kart>
    </div>
  );
}
