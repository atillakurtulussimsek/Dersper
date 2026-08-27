import { describe, expect, it } from "vitest";

import { buyut, kisaltmaOner } from "./kisaltma";

describe("buyut", () => {
  it("Türkçe i ve ı harflerini doğru büyütür", () => {
    expect(buyut("ilginç")).toBe("İLGİNÇ");
    expect(buyut("ışık")).toBe("IŞIK");
    expect(buyut("Fizik")).toBe("FİZİK");
  });
});

describe("kisaltmaOner", () => {
  it("yaygın dersleri tanır", () => {
    expect(kisaltmaOner("Türkçe")).toBe("TRK");
    expect(kisaltmaOner("Matematik")).toBe("MAT");
    expect(kisaltmaOner("Fen Bilimleri")).toBe("FEN");
    expect(kisaltmaOner("Sosyal Bilgiler")).toBe("SOS");
    expect(kisaltmaOner("İngilizce")).toBe("İNG");
    expect(kisaltmaOner("Din Kültürü ve Ahlak Bilgisi")).toBe("DKAB");
  });

  it("büyük-küçük harf ve fazla boşluğa takılmaz", () => {
    expect(kisaltmaOner("  matematik ")).toBe("MAT");
    expect(kisaltmaOner("FEN   BİLİMLERİ")).toBe("FEN");
  });

  it("bilinmeyen tek kelimede ilk üç harfi alır", () => {
    expect(kisaltmaOner("Felsefe")).toBe("FEL");
    expect(kisaltmaOner("Robotik")).toBe("ROB");
  });

  it("üç ve daha fazla kelimede baş harfleri alır, bağlaçları atlar", () => {
    expect(kisaltmaOner("Proje Tasarım Atölyesi")).toBe("PTA");
    expect(kisaltmaOner("Çevre ve Bilim Uygulamaları")).toBe("ÇBU");
  });

  it("iki kelimede ilk kelimenin ilk üç harfini alır", () => {
    expect(kisaltmaOner("Uygulamalı Bilimler")).toBe("UYG");
  });

  it("seviye ekini korur", () => {
    expect(kisaltmaOner("Matematik 2")).toBe("MAT2");
    expect(kisaltmaOner("Fizik II")).toBe("FİZII");
  });

  it("boş ve anlamsız girdide boş döner", () => {
    expect(kisaltmaOner("")).toBe("");
    expect(kisaltmaOner("   ")).toBe("");
    expect(kisaltmaOner("123")).toBe("");
  });
});
