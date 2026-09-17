const assert = require("node:assert/strict");
const test = require("node:test");
const {buildCommandTransaction} = require("../src/editor_commands.js");

function apply(document, transaction) {
  return document.slice(0, transaction.from)
    + transaction.insert
    + document.slice(transaction.to);
}

test("selected and empty formatting commands produce one portable edit", () => {
  const bold = buildCommandTransaction("word", 0, 4, "bold");
  assert.equal(apply("word", bold), "**word**");
  assert.deepEqual(bold.selection, {anchor: 2, head: 6});

  const italic = buildCommandTransaction("", 0, 0, "italic");
  assert.equal(apply("", italic), "**");
  assert.deepEqual(italic.selection, {anchor: 1, head: 1});

  const code = buildCommandTransaction("", 0, 0, "code");
  assert.equal(apply("", code), "``");
  assert.deepEqual(code.selection, {anchor: 1, head: 1});
});

test("heading prefixes the current line and link uses editable placeholders", () => {
  const heading = buildCommandTransaction("first\nsecond", 8, 8, "heading");
  assert.equal(apply("first\nsecond", heading), "first\n# second");
  assert.deepEqual(heading.selection, {anchor: 10, head: 10});

  const firstEmptyLine = buildCommandTransaction("\nsecond", 0, 0, "heading");
  assert.equal(apply("\nsecond", firstEmptyLine), "# \nsecond");

  const selectedLink = buildCommandTransaction("word", 0, 4, "link");
  assert.equal(apply("word", selectedLink), "[word](url)");
  assert.deepEqual(selectedLink.selection, {anchor: 7, head: 10});

  const emptyLink = buildCommandTransaction("", 0, 0, "link");
  assert.equal(apply("", emptyLink), "[text](url)");
  assert.deepEqual(emptyLink.selection, {anchor: 1, head: 5});
});

test("unknown toolbar command produces no transaction", () => {
  assert.equal(buildCommandTransaction("text", 0, 4, "unknown"), null);
});
