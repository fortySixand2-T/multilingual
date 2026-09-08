import { VocabCard } from "./api";
import AudioButton from "./AudioButton";

// The French headword of a vocab card with its gender shown to the learner:
//   "m"  → "café (m)"        "f"  → "eau (fe)"
//   "mf" → "ami (m) / amie (fe)"  — both forms, each with its own pronunciation
//   ""   → just the word (verbs, adverbs, phrases…)
// Used on the flashcard front; the audio keys come from the API (fr → `audio`,
// feminine form → `fem_audio`).
const BIG = { fontSize: 34, fontWeight: 800 } as const;

// gender code → the marker a learner sees next to the word
const MARK = { m: "(m)", f: "(fe)" } as const;

// Epicene nouns: invariant spelling, but the article/agreement varies with the
// referent's sex ("le témoin" / "la témoin"). The content schema's `gender`
// field has no bucket for this (it's authored "m" for lack of a better fit,
// since there's no distinct feminine spelling to put in `fem`), so a plain
// "(m)" badge would wrongly assert these words are grammatically masculine
// only. Flag the handful of known epicene ids so they get a "(m/f)" badge
// instead — see qa/issues/720-epicene-nouns-always-shown-as-m-le.md.
const EPICENE_IDS = new Set([
  "temoin",
  "psychologue",
  "notaire",
  "actionnaire",
  "apatride",
  "autochtone",
  "camarade",
  "specialiste",
]);

export default function VocabWord({ card }: { card: VocabCard }) {
  // dual-gender: show both forms side by side, each with its own pronunciation
  if (card.gender === "mf") {
    return (
      <div className="vocab-word">
        <span style={BIG}>
          {card.fr} <span className="gender-mark">{MARK.m}</span>
        </span>
        {card.audio && <AudioButton key={`${card.id}-m`} audioKey={card.audio} label="🔊" slow />}
        <span className="muted" style={{ fontSize: 26, fontWeight: 800 }}>/</span>
        <span style={BIG}>
          {card.fem} <span className="gender-mark">{MARK.f}</span>
        </span>
        {card.fem_audio && <AudioButton key={`${card.id}-f`} audioKey={card.fem_audio} label="🔊" slow />}
      </div>
    );
  }

  const epicene = EPICENE_IDS.has(card.id);
  const marked = card.gender === "m" || card.gender === "f";
  return (
    <div className="vocab-word">
      <span style={BIG}>
        {card.fr}
        {epicene ? (
          <> <span className="gender-mark">(m/f)</span></>
        ) : (
          marked && <> <span className="gender-mark">{MARK[card.gender as "m" | "f"]}</span></>
        )}
      </span>
      {card.audio && <AudioButton key={card.id} audioKey={card.audio} label="🔊" slow />}
    </div>
  );
}
