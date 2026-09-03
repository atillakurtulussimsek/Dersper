import { describe, expect, it } from "vitest";

import { ogretmenleriGrupla } from "./ogretmenSirasi";
import type { MufredatSatiri, Ogretmen } from "./types";

const o = (id: number, full_name: string, branch: string | null): Ogretmen =>
  ({ id, full_name, branch } as Ogretmen);

const ogretmenler = [
  o(1, "Zeynep Kaya", "Matematik"),
  o(2, "Ali Çelik", "Türkçe"),
  o(3, "Ayşe Yılmaz", null),
  o(4, "Mehmet Demir", "Fen Bilimleri"),
];

describe("ogretmenleriGrupla", () => {
  it("branşı derse uyanları öne, gerisini ada göre sonraya koyar", () => {
    const { brans, diger } = ogretmenleriGrupla(ogretmenler, 10, "Matematik", []);
    expect(brans.map((x) => x.full_name)).toEqual(["Zeynep Kaya"]);
    expect(diger.map((x) => x.full_name)).toEqual(["Ali Çelik", "Ayşe Yılmaz", "Mehmet Demir"]);
  });

  it("dersi zaten okutan öğretmeni branşı yazmasa da öne alır", () => {
    const mufredat = [{ subject_id: 10, teacher_id: 3 } as MufredatSatiri];
    const { brans } = ogretmenleriGrupla(ogretmenler, 10, "Matematik", mufredat);
    expect(brans.map((x) => x.full_name)).toEqual(["Ayşe Yılmaz", "Zeynep Kaya"]);
  });

  it("Türkçe büyük/küçük harfe ve içermeye toleranslı", () => {
    const { brans } = ogretmenleriGrupla([o(5, "İpek", "FEN")], 1, "Fen Bilimleri", []);
    expect(brans).toHaveLength(1);
  });

  it("ders seçilmemişse herkes 'diğer'de, ada göre", () => {
    const { brans, diger } = ogretmenleriGrupla(ogretmenler, null, null, []);
    expect(brans).toEqual([]);
    expect(diger[0].full_name).toBe("Ali Çelik");
  });
});
