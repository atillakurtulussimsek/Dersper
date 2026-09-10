/** Aralar (öğle, teneffüs) programda satır/sütun değildir; dersler aralar
 *  atlanarak numaralanır. Sunucu tarafı işaretleme ile doğrulanır. */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import CarsafIzgarasi from "./CarsafIzgarasi";
import ProgramIzgarasi from "./ProgramIzgarasi";
import type { Gun, Hucre } from "../lib/types";

const GUNLER = ["Pazartesi", "Salı"];

/** 8 satır: 5. sırada (index 4) öğle arası, 3. sırada (index 2) teneffüs. */
function gunler(): Gun[] {
  return GUNLER.map((ad, gi) => ({
    id: gi + 1, index: gi, name: ad, is_active: true,
    periods: Array.from({ length: 8 }, (_, i) => ({
      id: gi * 10 + i + 1, day_id: gi + 1, index: i,
      name: i === 4 ? "Öğle arası" : i === 2 ? "Teneffüs" : `${i + 1}. ders`,
      start_time: null, end_time: null,
      is_break: i === 4 || i === 2, is_lunch: i === 4,
    })),
  }));
}

function hucre(gun: number, saat: number): Hucre {
  return {
    assignment_id: gun * 100 + saat, period_id: gun * 10 + saat + 1,
    day_index: gun, period_index: saat,
    section_id: 1, section_name: "9-A", section_ids: [1], section_names: ["9-A"],
    subject_name: "Matematik", subject_short: "MAT", subject_color: "#3b82f6",
    teacher_id: 7, teacher_name: "Ayşe Yılmaz", teacher_short: "AY", is_locked: false,
  };
}

describe("aralar ders saati olarak görünmez", () => {
  it("ayrı sayfa: 6 ders satırı, 1'den 6'ya, öğle ve teneffüs yok", () => {
    const html = renderToStaticMarkup(
      <ProgramIzgarasi gunler={gunler()} hucreler={[hucre(0, 0), hucre(0, 7)]}
        bakis="sube" anahtar="9-A" duzenlenebilir={false} />,
    );
    for (const n of [1, 2, 3, 4, 5, 6]) expect(html).toContain(`>${n}.<`);
    expect(html).not.toContain(">7.<");
    expect(html).not.toContain(">8.<");
    expect(html).not.toMatch(/öğle|teneffüs/);
    expect((html.match(/<tr>/g) ?? []).length).toBe(1 + 6); // başlık + 6 satır
    // Son saatteki ders (index 7) 6. satırda görünür.
    expect(html).toContain("Matematik");
  });

  it("çarşaf: her gün 6 sütun, 1'den 6'ya numaralı", () => {
    const html = renderToStaticMarkup(
      <CarsafIzgarasi gunler={gunler()} hucreler={[hucre(0, 5), hucre(1, 7)]} bakis="sube" />,
    );
    expect(html).not.toMatch(/öğle|teneffüs/);
    expect(html).toContain('colSpan="6"');
    expect((html.match(/>6<\/th>/g) ?? []).length).toBe(2);
    expect(html).not.toContain(">7</th>");
    expect(html).not.toContain(">8</th>");
  });
});
