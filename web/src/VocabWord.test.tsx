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

  it("groups each dual-gender form with its own audio button so wrapping never splits them", () => {
    const { container } = render(
      <VocabWord
        card={{ ...base, fr: "docteur", gender: "mf", fem: "docteure", audio: "a/d.mp3", fem_audio: "a/d_f.mp3" }}
      />,
    );
    const forms = container.querySelectorAll(".vocab-form");
    expect(forms).toHaveLength(2);
    expect(forms[0]).toHaveTextContent("docteur");
    expect(forms[1]).toHaveTextContent("docteure");
    forms.forEach((f) => expect(f.querySelectorAll("button")).toHaveLength(1));
  });

  it("shows no marker for an ungendered word", () => {
    render(<VocabWord card={{ ...base, fr: "un", gender: "" }} />);
    expect(screen.getByText("un")).toBeInTheDocument();
    expect(screen.queryByText("(m)")).not.toBeInTheDocument();
    expect(screen.queryByText("(fe)")).not.toBeInTheDocument();
  });

  it("marks a known epicene noun (m)-only in the data with (m/f), not a plain (m)", () => {
    // témoin is authored gender:"m" (no distinct feminine spelling exists), but
    // "la témoin" is equally correct — the plain (m) badge would wrongly assert
    // it's masculine-only. See qa/issues/720-epicene-nouns-always-shown-as-m-le.md.
    render(<VocabWord card={{ ...base, id: "temoin", fr: "témoin", gender: "m" }} />);
    expect(screen.getByText("(m/f)")).toBeInTheDocument();
    expect(screen.queryByText("(m)")).not.toBeInTheDocument();
  });

  it("shows the IPA under the word", () => {
    render(<VocabWord card={{ ...base, fr: "paquet", gender: "m", ipa: "pakɛ" }} />);
    expect(screen.getByText("/pakɛ/")).toBeInTheDocument();
  });

  it("shows both IPAs for a dual-gender word, and none when absent", () => {
    const { container } = render(
      <VocabWord card={{ ...base, fr: "ami", gender: "mf", fem: "amie", ipa: "ami", fem_ipa: "ami" }} />,
    );
    expect(screen.getByText("/ami/ · /ami/")).toBeInTheDocument();
    render(<VocabWord card={{ ...base, fr: "un", gender: "" }} />);
    expect(container.ownerDocument.querySelectorAll(".vocab-ipa")).toHaveLength(1);
  });
});
