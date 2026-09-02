import { describe, expect, it } from "vitest";

import { dakikaya, saatSorunlari } from "./cakisma";

const ders = (name: string, start_time: string | null, end_time: string | null) => ({
  name,
  start_time,
  end_time,
  is_break: false,
});

describe("dakikaya", () => {
  it("saati dakikaya çevirir", () => {
    expect(dakikaya("09:20")).toBe(560);
    expect(dakikaya("09:20:00")).toBe(560);
  });

  it("boş saati geçirir", () => {
    expect(dakikaya(null)).toBeNull();
    expect(dakikaya("")).toBeNull();
  });
});

describe("saatSorunlari", () => {
  it("düzgün ızgarada sorun bulmaz", () => {
    expect(
      saatSorunlari([ders("1. ders", "09:00", "09:40"), ders("2. ders", "09:50", "10:30")]),
    ).toEqual([]);
  });

  it("saatleri boş bırakılmış ızgarayı sorun saymaz", () => {
    expect(saatSorunlari([ders("1. ders", null, null)])).toEqual([]);
  });

  it("üst üste binen ders saatlerini bulur", () => {
    const sonuc = saatSorunlari([
      ders("1. ders", "09:00", "09:40"),
      ders("2. ders", "09:20", "10:00"),
    ]);
    expect(sonuc).toHaveLength(1);
    expect(sonuc[0].tur).toBe("cakisma");
    expect(sonuc[0].metin).toContain("1. ders");
    expect(sonuc[0].metin).toContain("2. ders");
  });

  it("uç uca saatleri çakışma saymaz", () => {
    expect(
      saatSorunlari([ders("1. ders", "09:00", "09:40"), ders("2. ders", "09:40", "10:20")]),
    ).toEqual([]);
  });

  it("teneffüsle çakışmayı sorun saymaz", () => {
    const sonuc = saatSorunlari([
      ders("1. ders", "09:00", "09:40"),
      { name: "Teneffüs", start_time: "09:30", end_time: "09:50", is_break: true },
    ]);
    expect(sonuc.filter((s) => s.tur === "cakisma")).toEqual([]);
  });

  it("sıra dışı saati bulur", () => {
    const sonuc = saatSorunlari([
      ders("1. ders", "10:00", "10:40"),
      ders("2. ders", "09:00", "09:40"),
    ]);
    expect(sonuc.map((s) => s.tur)).toContain("sira");
  });

  it("yarım girilmiş ve ters saati bulur", () => {
    expect(saatSorunlari([ders("1. ders", "09:00", null)])[0].tur).toBe("eksik");
    expect(saatSorunlari([ders("1. ders", "10:00", "09:00")])[0].tur).toBe("eksik");
  });
});
