import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import VocabWord from "./VocabWord";

// Stub the audio button so we can assert which pronunciation keys are offered.
vi.mock("./AudioButton", () => ({
  default: ({ audioKey }: { audioKey: string }) => <button data-audio={audioKey}>🔊</button>,
}));

const base = { id: "x", en: "x" };
const audioKeys = () =>
  Array.from(document.querySelectorAll("[data-audio]")).map((n) => n.getAttribute("data-audio"));

describe("VocabWord gender display", () => {
  it("marks a masculine noun with (m)", () => {
    render(<VocabWord card={{ ...base, fr: "café", gender: "m", audio: "a/café.mp3" }} />);
    expect(screen.getByText("café")).toBeInTheDocument();
    expect(screen.getByText("(m)")).toBeInTheDocument();
    expect(audioKeys()).toEqual(["a/café.mp3"]);
  });

  it("marks a feminine noun with (fe)", () => {
    render(<VocabWord card={{ ...base, fr: "eau", gender: "f" }} />);
    expect(screen.getByText("(fe)")).toBeInTheDocument();
  });

  it("shows both forms + both pronunciations for a dual-gender word", () => {
    render(
      <VocabWord
        card={{
          ...base,
          fr: "serveur",
          gender: "mf",
          fem: "serveuse",
          audio: "a/serveur.mp3",
          fem_audio: "a/serveur_f.mp3",
        }}
      />,
    );
    expect(screen.getByText("serveur")).toBeInTheDocument();
    expect(screen.getByText("serveuse")).toBeInTheDocument();
    expect(screen.getByText("(m)")).toBeInTheDocument();
    expect(screen.getByText("(fe)")).toBeInTheDocument();
    expect(audioKeys()).toEqual(["a/serveur.mp3", "a/serveur_f.mp3"]);
  });

  it("shows no marker for an ungendered word", () => {
    render(<VocabWord card={{ ...base, fr: "un", gender: "" }} />);
    expect(screen.getByText("un")).toBeInTheDocument();
    expect(screen.queryByText("(m)")).not.toBeInTheDocument();
    expect(screen.queryByText("(fe)")).not.toBeInTheDocument();
  });
});
