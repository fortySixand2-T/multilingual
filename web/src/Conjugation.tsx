// A verb's present tense, one row per subject pronoun — checked Wiktionary data from
// /content/vocab, never model-generated.
export default function Conjugation({ rows }: { rows: [string, string][] }) {
  return (
    <table className="conjugation">
      <caption className="muted">Present tense</caption>
      <tbody>
        {rows.map(([subject, verb]) => (
          <tr key={subject}>
            <th scope="row">{subject}</th>
            <td>{verb}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
