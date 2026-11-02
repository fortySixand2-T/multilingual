import { describe, expect, it } from "vitest";
import { passageParagraphs } from "./passageParagraphs";

describe("passageParagraphs", () => {
  it("splits on blank lines and joins hard-wrapped lines", () => {
    expect(passageParagraphs("Un deux\ntrois.\n\nQuatre\ncinq.\n")).toEqual(["Un deux trois.", "Quatre cinq."]);
  });

  it("uses non-breaking spaces around guillemets and before : ? !", () => {
    expect(passageParagraphs("Il dit : « Peut-on\nvivre ? » Oui !")).toEqual([
      "Il dit : « Peut-on vivre ? » Oui !",
    ]);
  });

  it("keeps the line breaks of a menu, a letter and an itinerary", () => {
    expect(passageParagraphs("MENU DU JOUR — 15 €\nEntrée : soupe\nPlat : poulet")).toEqual([
      "MENU DU JOUR — 15 €\nEntrée\u00a0: soupe\nPlat\u00a0: poulet",
    ]);
    expect(passageParagraphs("Salut Sophie,\nJ'organise un dîner.")).toEqual(["Salut Sophie,\nJ'organise un dîner."]);
    const day = "Jour 1 : arrivée à l'aéroport, installation à l'hôtel, dîner au centre-ville.";
    expect(passageParagraphs(`${day}\nJour 2 : visite.`)[0]).toContain("centre-ville.\nJour 2");
  });

  it("joins a wrapped line that ends a sentence when the line is full width", () => {
    const line = "Les employés disent mieux concilier travail et vie familiale, et la plupart.";
    expect(passageParagraphs(`${line}\nSelon les auteurs, oui.`)).toEqual([`${line} Selon les auteurs, oui.`]);
  });
});
