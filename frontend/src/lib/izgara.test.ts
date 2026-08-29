import { describe, expect, it } from "vitest";

import { adlariTazele, otomatikAdMi, type AdlanabilirSaat } from "./izgara";

function ders(name: string): AdlanabilirSaat {
  return { name, is_break: false, is_lunch: false };
}
function teneffus(name = "Teneffüs"): AdlanabilirSaat {
  return { name, is_break: true, is_lunch: false };
}
function ogle(name = "Öğle arası"): AdlanabilirSaat {
  return { name, is_break: true, is_lunch: true };
}

const adlar = (s: AdlanabilirSaat[]) => s.map((p) => p.name);

describe("otomatikAdMi", () => {
  it("uygulamanın ürettiği adları tanır", () => {
    expect(otomatikAdMi("1. ders")).toBe(true);
    expect(otomatikAdMi("12. ders")).toBe(true);
    expect(otomatikAdMi("Teneffüs")).toBe(true);
    expect(otomatikAdMi("Öğle arası")).toBe(true);
  });

  it("kullanıcının yazdığı adları tanımaz", () => {
    expect(otomatikAdMi("Etüt")).toBe(false);
    expect(otomatikAdMi("Kahvaltı")).toBe(false);
    expect(otomatikAdMi("1. Ders")).toBe(false); // büyük harf: elle yazılmış
    expect(otomatikAdMi("Büyük teneffüs")).toBe(false);
  });
});

describe("adlariTazele", () => {
  it("araya teneffüs girince dersleri yeniden numaralar", () => {
    const sonra = adlariTazele([
      ders("1. ders"),
      teneffus(),
      ders("2. ders"),
      ders("3. ders"),
    ]);
    expect(adlar(sonra)).toEqual(["1. ders", "Teneffüs", "2. ders", "3. ders"]);
  });

  it("sıra değişince numaralar konuma göre yazılır", () => {
    // Sona eklenen satır başa çekilmiş.
    const sonra = adlariTazele([ders("3. ders"), ders("1. ders"), ders("2. ders")]);
    expect(adlar(sonra)).toEqual(["1. ders", "2. ders", "3. ders"]);
  });

  it("teneffüsler ders sayısına katılmaz", () => {
    const sonra = adlariTazele([
      ders("5. ders"),
      teneffus(),
      ogle(),
      ders("9. ders"),
    ]);
    expect(adlar(sonra)).toEqual(["1. ders", "Teneffüs", "Öğle arası", "2. ders"]);
  });

  it("teneffüs olan satırın otomatik adı teneffüse döner", () => {
    const sonra = adlariTazele([ders("1. ders"), teneffus("3. ders")]);
    expect(adlar(sonra)).toEqual(["1. ders", "Teneffüs"]);
  });

  it("öğle arası teneffüsten ayrı adlandırılır", () => {
    const sonra = adlariTazele([ders("1. ders"), ogle("Teneffüs")]);
    expect(adlar(sonra)).toEqual(["1. ders", "Öğle arası"]);
  });

  it("elle yazılmış adlara dokunmaz ama numaralandırmayı sürdürür", () => {
    const sonra = adlariTazele([
      ders("Etüt"),
      ders("7. ders"),
      teneffus("Büyük teneffüs"),
      ders("8. ders"),
    ]);
    // "Etüt" bir ders saati olduğu için sayılır; sonraki ders 2 olur.
    expect(adlar(sonra)).toEqual(["Etüt", "2. ders", "Büyük teneffüs", "3. ders"]);
  });

  it("değişmeyen satırlar için aynı nesneyi döndürür", () => {
    const girdi = [ders("1. ders"), teneffus()];
    const sonra = adlariTazele(girdi);
    expect(sonra[0]).toBe(girdi[0]);
    expect(sonra[1]).toBe(girdi[1]);
  });
});
