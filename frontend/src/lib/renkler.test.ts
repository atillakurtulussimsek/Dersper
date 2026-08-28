import { describe, expect, it } from "vitest";

import { PALET, rastgeleRenk } from "./renkler";

describe("rastgeleRenk", () => {
  it("her zaman paletten bir renk döner", () => {
    for (let i = 0; i < 50; i++) {
      expect(PALET).toContain(rastgeleRenk());
    }
  });

  it("kullanılmayan renklere öncelik verir", () => {
    const kullanilan = PALET.slice(0, PALET.length - 1);
    const beklenen = PALET[PALET.length - 1];
    for (let i = 0; i < 20; i++) {
      expect(rastgeleRenk([...kullanilan])).toBe(beklenen);
    }
  });

  it("büyük-küçük harf farkını yok sayar", () => {
    const kullanilan = PALET.slice(0, PALET.length - 1).map((r) => r.toUpperCase());
    expect(rastgeleRenk(kullanilan)).toBe(PALET[PALET.length - 1]);
  });

  it("palet tükendiğinde yine de renk döner", () => {
    expect(PALET).toContain(rastgeleRenk([...PALET]));
  });
});
