const NBSP = " ";

// Prose is authored wrapped at ~80 columns; shorter lines are deliberate (a menu, a
// timetable, "Salut Sophie,"), as is a line before a "Jour 2 :" or "Salaire :" item.
const WRAP_WIDTH = 70;
const ITEM = /^(\S+( \d+)?) :|^[-•–]/;

const isWrap = (line: string, next: string) =>
  /^[a-zà-ÿ]/.test(next) || (line.length >= WRAP_WIDTH && !ITEM.test(next));

/** Reading passages are authored hard-wrapped; paragraphs are separated by blank lines.
 *  Rejoin wrapped lines, keep deliberate line breaks as "\n" (render with pre-line), and
 *  keep French punctuation glued to its neighbour. */
export function passageParagraphs(passage: string): string[] {
  return passage
    .split(/\n\s*\n/)
    .map((p) =>
      p
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)
        .reduce((text, line, i, lines) => (i ? text + (isWrap(lines[i - 1], line) ? " " : "\n") + line : line), "")
        .replace(/«\s+/g, `«${NBSP}`)
        .replace(/\s+([»:;?!])/g, `${NBSP}$1`)
        .trim(),
    )
    .filter(Boolean);
}
