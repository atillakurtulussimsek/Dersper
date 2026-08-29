/** Kurum kullanıcıları.
 *
 *  Rol ayrımı yoktur: kuruma eklenen herkes yöneticidir. Bir hesap yalnızca bir
 *  kuruma bağlanabildiği için e-posta sistem genelinde eşsizdir.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, UserCheck, UserX } from "lucide-react";

import {
  Alan, Buton, Girdi, Kart, Kutu, Rozet, Tablo, Uyari, Yukleniyor,
} from "../components/ui";
import { get, post, put } from "../lib/api";
import type { Kullanici } from "../lib/types";

const BOS = { full_name: "", email: "", password: "" };

export default function Kullanicilar() {
  const qc = useQueryClient();
  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Kullanici | null>(null);
  const [form, setForm] = useState(BOS);

  const liste = useQuery({
    queryKey: ["kullanicilar"],
    queryFn: () => get<Kullanici[]>("/users"),
  });
  const ben = useQuery({ queryKey: ["ben"], queryFn: () => get<Kullanici>("/auth/me") });

  const tazele = () => qc.invalidateQueries({ queryKey: ["kullanicilar"] });

  const kaydet = useMutation({
    mutationFn: () =>
      duzenlenen
        ? put<Kullanici>(`/users/${duzenlenen.id}`, {
            full_name: form.full_name,
            is_active: duzenlenen.is_active,
            password: form.password || null,
          })
        : post<Kullanici>("/users", form),
    onSuccess: () => {
      tazele();
      setAcik(false);
    },
  });

  const durumDegistir = useMutation({
    mutationFn: (k: Kullanici) =>
      put<Kullanici>(`/users/${k.id}`, {
        full_name: k.full_name,
        is_active: !k.is_active,
      }),
    onSuccess: tazele,
  });

  function ac(k?: Kullanici) {
    setDuzenlenen(k ?? null);
    setForm(k ? { full_name: k.full_name, email: k.email, password: "" } : BOS);
    setAcik(true);
  }

  const hata = [kaydet, durumDegistir].find((m) => m.error)?.error as Error | undefined;

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Kullanıcılar</h1>
          <p className="text-sm text-murekkep-silik">
            Kurumunuzda çalışan hesaplar. Eklediğiniz herkes sizinle aynı yetkilere
            sahiptir.
          </p>
        </div>
        <Buton onClick={() => ac()}>
          <Plus className="h-4 w-4" /> Kullanıcı ekle
        </Buton>
      </header>

      {hata && <Uyari tur="hata">{hata.message}</Uyari>}

      <Uyari>
        Bir hesap yalnızca bir kuruma bağlanabilir. Aynı kişi başka bir kurumda da
        çalışacaksa o kurum için ayrı bir e-postayla hesap açması gerekir.
      </Uyari>

      <Kart>
        {liste.isLoading ? (
          <Yukleniyor />
        ) : (
          <Tablo basliklar={["Ad soyad", "E-posta", "Durum", ""]}>
            {liste.data?.map((k) => (
              <tr key={k.id} className="hover:bg-yuzey-alt">
                <td className="px-3 py-2.5">
                  <span className="flex items-center gap-2">
                    <span className="font-medium">{k.full_name}</span>
                    {k.id === ben.data?.id && <Rozet>siz</Rozet>}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-murekkep-silik">{k.email}</td>
                <td className="px-3 py-2.5">
                  <Rozet tur={k.is_active ? "iyi" : "kotu"}>
                    {k.is_active ? "Açık" : "Kapalı"}
                  </Rozet>
                </td>
                <td className="px-3 py-2.5 text-right">
                  <div className="flex justify-end gap-1">
                    <Buton tur="sade" onClick={() => ac(k)} aria-label="Düzenle">
                      <Pencil className="h-4 w-4" />
                    </Buton>
                    {k.id !== ben.data?.id && (
                      <Buton
                        tur="sade"
                        aria-label={k.is_active ? "Hesabı kapat" : "Hesabı aç"}
                        title={k.is_active ? "Hesabı kapat" : "Hesabı aç"}
                        onClick={() => {
                          if (
                            !k.is_active ||
                            confirm(
                              `"${k.full_name}" hesabı kapatılsın mı?\n\n` +
                                "Giriş yapamaz. İstediğiniz zaman yeniden açabilirsiniz.",
                            )
                          )
                            durumDegistir.mutate(k);
                        }}
                      >
                        {k.is_active ? (
                          <UserX className="h-4 w-4 text-hata" />
                        ) : (
                          <UserCheck className="h-4 w-4 text-basari" />
                        )}
                      </Buton>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </Tablo>
        )}
      </Kart>

      <Kutu
        acik={acik}
        kapat={() => setAcik(false)}
        baslik={duzenlenen ? "Kullanıcıyı düzenle" : "Kullanıcı ekle"}
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            kaydet.mutate();
          }}
        >
          <Alan etiket="Ad soyad">
            <Girdi
              required
              autoFocus
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
          </Alan>

          <Alan
            etiket="E-posta"
            ipucu={duzenlenen ? "E-posta değiştirilemez." : undefined}
          >
            <Girdi
              required
              type="email"
              value={form.email}
              disabled={Boolean(duzenlenen)}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              autoComplete="off"
            />
          </Alan>

          <Alan
            etiket={duzenlenen ? "Yeni parola" : "Parola"}
            ipucu={
              duzenlenen
                ? "Değiştirmek istemiyorsanız boş bırakın."
                : "En az 8 karakter. Kullanıcıya kendiniz iletirsiniz."
            }
          >
            <Girdi
              required={!duzenlenen}
              minLength={8}
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              autoComplete="new-password"
            />
          </Alan>

          {kaydet.error && <Uyari tur="hata">{(kaydet.error as Error).message}</Uyari>}

          <div className="flex justify-end gap-2 pt-2">
            <Buton tur="ikincil" type="button" onClick={() => setAcik(false)}>
              Vazgeç
            </Buton>
            <Buton type="submit" yukleniyor={kaydet.isPending}>
              Kaydet
            </Buton>
          </div>
        </form>
      </Kutu>
    </div>
  );
}
