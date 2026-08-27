import { describe, expect, it } from "vitest";

import { buyut, kisaltmaOner, ogretmenKoduOner } from "./kisaltma";

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

describe("ogretmenKoduOner", () => {
  it("ad ve soyadın baş harflerini alır", () => {
    expect(ogretmenKoduOner("Beyhan Karagöz")).toBe("BK");
    expect(ogretmenKoduOner("Atilla ŞİMŞEK")).toBe("AŞ");
    expect(ogretmenKoduOner("Saadet POYRAZ SOYDAN")).toBe("SPS");
  });

  it("küçük harf ve fazla boşluğa takılmaz", () => {
    expect(ogretmenKoduOner("  ayşe   yılmaz ")).toBe("AY");
    expect(ogretmenKoduOner("ismail ışık")).toBe("İI");
  });

  it("unvanları atlar", () => {
    expect(ogretmenKoduOner("Dr. Mehmet Kaya")).toBe("MK");
  });

  it("en fazla dört harf alır", () => {
    expect(ogretmenKoduOner("Ali Veli Ahmet Mehmet Hasan")).toBe("AVAM");
  });

  it("çakışan kodu sayıyla benzersizleştirir", () => {
    expect(ogretmenKoduOner("Ayşe Kaya", ["AK"])).toBe("AK2");
    expect(ogretmenKoduOner("Ayşe Kaya", ["AK", "AK2"])).toBe("AK3");
    expect(ogretmenKoduOner("Ayşe Kaya", ["ZZ"])).toBe("AK");
  });

  it("boş girdide boş döner", () => {
    expect(ogretmenKoduOner("")).toBe("");
    expect(ogretmenKoduOner("  ")).toBe("");
  });
});
