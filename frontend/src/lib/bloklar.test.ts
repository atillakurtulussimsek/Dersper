import { describe, expect, it } from "vitest";

import { desenCoz, desenEtiketi, desenOnerileri } from "./bloklar";

describe("desenCoz", () => {
  it("deseni çözer", () => {
    expect(desenCoz("2+2+1", 5).bloklar).toEqual([2, 2, 1]);
    expect(desenCoz("1+1+2+1", 5).bloklar).toEqual([1, 1, 2, 1]);
  });

  it("ayraçlarda esnek", () => {
    expect(desenCoz("2, 2 ,1", 5).bloklar).toEqual([2, 2, 1]);
    expect(desenCoz(" 2 2 1 ", 5).bloklar).toEqual([2, 2, 1]);
  });

  it("boş desen tek saatlere açılır", () => {
    expect(desenCoz("", 3).bloklar).toEqual([1, 1, 1]);
    expect(desenCoz("  ", 3).gecerli).toBe(true);
  });

  it("toplam tutmazsa geçersiz sayar", () => {
    const s = desenCoz("2+2", 5);
    expect(s.gecerli).toBe(false);
    expect(s.hata).toContain("4 saat");
  });

  it("sayı olmayanı reddeder", () => {
    expect(desenCoz("2+x", 5).gecerli).toBe(false);
    expect(desenCoz("0+5", 5).hata).toContain("en az 1");
    expect(desenCoz("9", 9).hata).toContain("en fazla");
  });
});

describe("desenOnerileri", () => {
  it("önerilerin toplamı haftalık saati tutar", () => {
    for (let saat = 1; saat <= 12; saat++) {
      for (const desen of desenOnerileri(saat)) {
        expect(desenCoz(desen, saat).gecerli).toBe(true);
      }
    }
  });

  it("beş saat için beklenen desenleri üretir", () => {
    const o = desenOnerileri(5);
    expect(o[0]).toBe("1+1+1+1+1");
    expect(o).toContain("2+2+1");
  });

  it("sıfır saatte boş döner", () => {
    expect(desenOnerileri(0)).toEqual([]);
  });
});

describe("desenEtiketi", () => {
  it("tek saatlik dağılımı sadeleştirir", () => {
    expect(desenEtiketi("1+1+1", 3)).toBe("tek saat");
    expect(desenEtiketi("", 3)).toBe("tek saat");
    expect(desenEtiketi("2+2+1", 5)).toBe("2+2+1");
  });
});
