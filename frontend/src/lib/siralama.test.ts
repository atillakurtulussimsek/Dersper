import { describe, expect, it } from "vitest";

import { dogalKarsilastir, siraKarsilastirici } from "./siralama";

describe("dogalKarsilastir", () => {
  it("sayıları sayı olarak sayar", () => {
    expect(["10-A", "9-B", "9-A"].sort(dogalKarsilastir)).toEqual(["9-A", "9-B", "10-A"]);
  });
});

describe("siraKarsilastirici", () => {
  it("verilen sırayı uygular, bilinmeyeni sona atar", () => {
    const k = siraKarsilastirici(["10-A", "9-A"]);
    expect(["9-A", "8-B", "10-A", "8-A"].sort(k)).toEqual(["10-A", "9-A", "8-A", "8-B"]);
  });
});
