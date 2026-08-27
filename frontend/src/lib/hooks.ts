/** Basit CRUD kaynakları için ortak sorgu yardımcıları. */
import {
  useMutation, useQuery, useQueryClient, type UseMutationResult,
} from "@tanstack/react-query";

import { del, get, post, put } from "./api";

export function useListe<T>(anahtar: string, yol: string) {
  return useQuery({ queryKey: [anahtar], queryFn: () => get<T[]>(yol) });
}

/** Ekleme / güncelleme / silme işlemlerini tek yerde toplar. */
export function useKaynak<Girdi, Cikti>(anahtar: string, yol: string) {
  const qc = useQueryClient();
  const tazele = () => qc.invalidateQueries({ queryKey: [anahtar] });

  const ekle = useMutation({
    mutationFn: (veri: Girdi) => post<Cikti>(yol, veri),
    onSuccess: tazele,
  });
  const guncelle = useMutation({
    mutationFn: ({ id, veri }: { id: number; veri: Girdi }) =>
      put<Cikti>(`${yol}/${id}`, veri),
    onSuccess: tazele,
  });
  const sil = useMutation({
    mutationFn: (id: number) => del(`${yol}/${id}`),
    onSuccess: tazele,
  });

  return { ekle, guncelle, sil, tazele };
}

export function hataMetni(...mutasyonlar: UseMutationResult<any, any, any>[]): string | null {
  for (const m of mutasyonlar) {
    if (m.error) return (m.error as Error).message;
  }
  return null;
}
