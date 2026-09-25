// Pure transaction specs for the editor's minimum Markdown toolbar.

const WRAPS = {
  bold: ["**", "**"],
  italic: ["*", "*"],
  code: ["`", "`"],
  strikethrough: ["~~", "~~"],
};

// Empty wrap selections place the caret between delimiters. Empty links insert
// [text](url) and select "text"; selected links select the "url" placeholder.
// Heading inserts a level-one prefix on the selection's current line only.
export function buildCommandTransaction(document, anchor, head, command) {
  const from = Math.min(anchor, head);
  const to = Math.max(anchor, head);
  const selected = document.slice(from, to);

  if (Object.hasOwn(WRAPS, command)) {
    const [prefix, suffix] = WRAPS[command];
    return {
      from,
      to,
      insert: `${prefix}${selected}${suffix}`,
      selection: {
        anchor: anchor + prefix.length,
        head: head + prefix.length,
      },
    };
  }

  if (command === "link") {
    const text = selected || "text";
    const insertion = `[${text}](url)`;
    const selectText = !selected;
    const start = from + 1;
    return {
      from,
      to,
      insert: insertion,
      selection: selectText
        ? {anchor: start, head: start + text.length}
        : {anchor: start + text.length + 2, head: start + text.length + 5},
    };
  }

  if (command === "heading") {
    const lineStart = document.slice(0, from).lastIndexOf("\n") + 1;
    return {
      from: lineStart,
      to: lineStart,
      insert: "# ",
      selection: {
        anchor: anchor >= lineStart ? anchor + 2 : anchor,
        head: head >= lineStart ? head + 2 : head,
      },
    };
  }

  const inserts = {
    bullet_list: "- ",
    ordered_list: "1. ",
    quote: "> ",
    horizontal_rule: "---\n",
    image: "![alt text](image-url)",
    table: "| Column 1 | Column 2 |\n| --- | --- |\n| Value | Value |",
    math: "$$\n\n$$",
    mermaid: "```mermaid\n\n```",
  };
  if (Object.hasOwn(inserts, command)) {
    const insert = inserts[command];
    return {
      from,
      to,
      insert,
      selection: { anchor: from, head: from + insert.length },
    };
  }

  return null;
}
