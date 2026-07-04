#!/usr/bin/env node
// Generates tests/oracle/regexp-vectors.json by running every vector through
// Node's own RegExp implementation. Each entry records
// {pattern, flags, input, op, replacement?, limit?, expected} where op is one
// of "test" | "replace" | "split" | "search".
//
// Constraints kept in sync with the Python engine subset
// (src/tsonic_python_js/regexp.py):
// - only constructs from the supported subset appear here;
// - split vectors never use capturing groups (the engine rejects them
//   because JS splices capture values into split output).
//
// Regenerate with: node tools/generate-regexp-oracle.mjs

import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const cases = [];
const test = (pattern, flags, input) => cases.push({ pattern, flags, input, op: "test" });
const search = (pattern, flags, input) => cases.push({ pattern, flags, input, op: "search" });
const split = (pattern, flags, input, limit) =>
  cases.push({ pattern, flags, input, op: "split", ...(limit === undefined ? {} : { limit }) });
const replace = (pattern, flags, input, replacement) =>
  cases.push({ pattern, flags, input, op: "replace", replacement });

// --- literals, dot, escapes -------------------------------------------------
test("abc", "", "xxabcxx");
test("abc", "", "xxabxcx");
test("a.c", "", "abc");
test("a.c", "", "a\nc");
test("a.c", "", "a\rc");
test("a.c", "", "a c");
test("a.c", "", "a c");
test("a\\.c", "", "abc");
test("a\\.c", "", "a.c");
test("\\+\\*\\?", "", "x+*?y");
test("a\\/b", "", "a/b");
test("\\\\", "", "back\\slash");
test("\\n", "", "line1\nline2");
test("\\t\\r\\f\\v", "", "a\t\r\f\vb");
test("\\x41\\u0042", "", "zABz");
test("\\x0a", "", "a\nb");
test("\\0", "", "a\0b");
test("\\$\\^\\[\\]\\(\\)\\{\\}\\|", "", "x$^[]{}()|y");
test("\\$\\^\\[\\]\\(\\)\\{\\}\\|", "", "x$^[](){}|y");
search("a.c", "", "zzabc");
search("q", "", "zzabc");
search("\\u0042", "", "aB");

// --- character classes ------------------------------------------------------
test("[abc]", "", "zzz");
test("[abc]", "", "zbz");
test("[a-z]+", "", "HELLO there");
test("[^a-z]", "", "abcZ");
test("[^a-z]", "", "abc");
test("[a-zA-Z0-9_]+", "", "!!id_42!!");
test("[-abc]", "", "x-y");
test("[abc-]", "", "x-y");
test("[\\]]", "", "a]b");
test("[\\d]+", "", "abc123");
test("[^\\d]+", "", "123");
test("[\\w\\s]+", "", "a b");
test("[a-c][x-z]", "", "by");
test("[a-c][x-z]", "", "bw");
test("[]a", "", "a");
test("[^]", "", "\n");
test("[\\b]", "", "a\bb");
test("[\\x61-\\x63]", "", "b");
test("[\\u0041-\\u005A]", "", "Q");
search("[0-9]", "", "abc42");

// --- class escapes in and out of classes ------------------------------------
test("\\d+", "", "order 66");
test("\\D+", "", "123");
test("\\D+", "", "123abc");
test("\\w+", "", "hi_there9");
test("\\W", "", "abc_123");
test("\\W", "", "abc!123");
test("\\s", "", "a b");
test("\\s", "", "a b");
test("\\s", "", "a　b");
test("\\s", "", "a﻿b");
test("\\s", "", "a​b");
test("\\s", "", "ab");
test("\\S+", "", "   x  ");
search("\\d", "", "abc123");
search("\\S", "", "   !");

// --- quantifiers ------------------------------------------------------------
test("ab*c", "", "ac");
test("ab*c", "", "abbbc");
test("ab+c", "", "ac");
test("ab+c", "", "abbc");
test("ab?c", "", "ac");
test("ab?c", "", "abc");
test("ab?c", "", "abbc");
test("a{3}", "", "aa");
test("a{3}", "", "aaa");
test("a{2,}", "", "aa");
test("a{2,}", "", "a");
test("a{2,4}b", "", "aaaaab");
test("a{2,4}b", "", "ab");
test("a{0,2}b", "", "b");
test("a{0}b", "", "b");
search("ba{2,3}", "", "xbaab");
replace("a{2,4}", "", "aaaaaa", "<$&>");
replace("x*", "", "yyy", "-");

// --- greedy backtracking ----------------------------------------------------
test(".*c", "", "abcabc");
replace(".*c", "", "abcabcd", "[$&]");
replace("a+a", "", "aaaa", "<$&>");
replace("[a-z]*bc", "", "xxabcbc!", "<$&>");
replace("(a*)*", "", "b", "<$1>");
replace("(a*)(a*)", "", "aa", "<$1|$2>");
replace("(?:(a)|(b))+", "", "ab", "<$1|$2>");
replace("(a|b)+", "", "abba", "<$1>");

// --- anchors with and without m ---------------------------------------------
test("^abc", "", "abcdef");
test("^abc", "", "xabc");
test("abc$", "", "xxabc");
test("abc$", "", "abcx");
test("^abc$", "", "abc");
test("^b", "", "a\nb");
test("^b", "m", "a\nb");
test("^b", "m", "a\rb");
test("^b", "m", "a b");
test("^b", "m", "a b");
test("b$", "", "b\na");
test("b$", "m", "b\na");
test("b$", "m", "b\ra");
test("b$", "m", "b a");
test("^$", "", "");
test("^$", "m", "a\n\nb");
replace("^a", "g", "aaa", "X");
replace("^", "m", "a\nb", "> ");
replace("^", "gm", "a\nb", "> ");
replace("$", "gm", "a\nb", "!");
replace("$", "gm", "a\r\nb", "!");
search("^b$", "m", "aa\nb\ncc");

// --- alternation precedence -------------------------------------------------
test("a|b", "", "zzb");
test("ab|cd", "", "acd");
replace("a|ab", "", "abc", "<$&>");
replace("ab|a", "", "abc", "<$&>");
replace("^x|y$", "g", "xzy", "-");
test("cat|dog|bird", "", "hotdog!");
replace("a(b|c)d", "", "zacdz", "[$1]");
search("b|c", "", "abc");

// --- groups and $n substitution ----------------------------------------------
replace("(\\d+)-(\\d+)", "", "call 12-34 now", "$2-$1");
replace("(\\w+) (\\w+)", "", "hello world", "$2 $1");
replace("(a+)(b*)", "", "aab", "[$1|$2]");
replace("(a+)(b*)", "", "aa", "[$1|$2]");
replace("(a)|(b)", "g", "ab", "<$1:$2>");
replace("((a)(b))", "", "ab", "$1-$2-$3");
replace("(a)", "", "a", "$2");
replace("(a)", "", "a", "$0");
replace("(a)", "", "a", "$$1");
replace("(a)", "", "a", "$&$&");
replace("(a)b", "", "xaby", "$`");
replace("(a)b", "", "xaby", "$'");
replace("(a)b", "", "xaby", "$");
replace("(a)b", "", "xaby", "x$");
replace("(a)b", "", "xaby", "$z");
replace("(\\d)(\\d)(\\d)(\\d)(\\d)(\\d)(\\d)(\\d)(\\d)(\\d)(\\d)", "", "01234567890", "$11|$10|$1");
replace("(\\d)", "", "7", "$07");
replace("a(?:bc)d", "", "xabcdy", "[$&]");
test("(?:ab)+", "", "ababab");

// --- i flag -------------------------------------------------------------------
test("abc", "i", "xAbCy");
test("[a-z]+", "i", "HELLO");
test("[^a-z]", "i", "AbC");
test("ÉCOLE", "i", "école");
test("école", "i", "ÉCOLE");
test("[à-ö]", "i", "Ä");
test("[à-ö]", "i", "ä");
test("s", "i", "ſ"); // long s: excluded by the ASCII guard in non-u mode
test("S", "i", "ſ");
test("k", "i", "K"); // Kelvin sign folds to itself in non-u mode
test("K", "i", "K");
test("K", "i", "k");
test("σ", "i", "ς"); // sigma vs final sigma
test("Σ", "i", "ς");
test("Σ", "i", "σ");
test("[σ]", "i", "ς");
test("[Σ]", "i", "ς");
test("[^σ]", "i", "ς");
test("µ", "i", "μ"); // micro sign vs greek mu
test("ß", "i", "ß"); // sharp s uppercases to "SS": folds to itself
test("ß", "i", "SS");
test("İ", "i", "i"); // dotted capital I
test("İ", "i", "İ");
replace("hello", "i", "say Hello twice Hello", "bye");
replace("hello", "gi", "say Hello twice heLLo", "bye");
search("b", "i", "aBc");

// --- g vs non-g replace -------------------------------------------------------
replace("o", "", "foo boo", "0");
replace("o", "g", "foo boo", "0");
replace("\\d+", "g", "a1b22c333", "#");
replace("\\d+", "", "a1b22c333", "#");
replace("\\s+", "g", "a  b\tc", " ");
replace("q", "g", "aaa", "z");

// --- split ---------------------------------------------------------------------
split(",", "", "a,b,c");
split(",", "", "a,,c");
split(",", "", ",a,");
split(",", "", "");
split("", "", "abc");
split("", "", "");
split("\\s*,\\s*", "", "a , b,c ,d");
split("\\s+", "", "a b  c");
split("(?:,|;)", "", "a,b;c");
split("x", "", "abc");
split("o", "g", "foo boo");
split("\\d", "", "a1b2c");
split("a*", "", "baaab");
split(",", "", "a,b,c", 0);
split(",", "", "a,b,c", 1);
split(",", "", "a,b,c", 2);
split(",", "", "a,b,c", 99);
split("", "", "abc", 2);
split("\\s+", "", "a b  c", 2);
split(",", "", "", 1);
split("a*", "", "baaab", 2);

// --- empty-match edge cases -----------------------------------------------------
replace("", "", "abc", "-");
replace("", "g", "abc", "-");
replace("a*", "g", "bab", "-");
replace("b*", "g", "abc", "!");
replace("$", "", "abc", "!");
replace("^", "", "abc", ">");
replace("x{0}", "g", "ab", ".");
test("a*", "", "");
search("a*", "", "bbb");

// --- unicode BMP chars -----------------------------------------------------------
test("你好", "", "说你好吗");
replace("好", "g", "好上加好", "x");
split("、", "", "一、二、三");
test("[α-ω]+", "", "χαος");
search("好", "", "说你好");
replace("[é]", "g", "café résumé", "e");

// --- UTF-16 surrogates (non-u mode works per code unit) ---------------------------
test(".", "", "\u{1f600}");
test("^.$", "", "\u{1f600}");
test("^..$", "", "\u{1f600}");
test("\\ud83d", "", "\u{1f600}");
test("\\ude00", "", "\u{1f600}");
test("[\\ud800-\\udbff]", "", "\u{1f600}");
test("[\\udc00-\\udfff][\\ud800-\\udbff]", "", "\u{1f600}");
test("\u{1f600}", "", "a\u{1f600}b");
test("[\u{1f600}]", "", "\ud83d");
search("\\ude00", "", "\u{1f600}");
search("b", "", "\u{1f600}b");
replace(".", "", "\u{1f600}", "x");
replace(".", "g", "\u{1f600}", "x");
replace("(.)(.)", "", "\u{1f600}", "$2$1");
replace("x*", "g", "a\u{1f600}b", "-");
replace("\u{1f600}", "g", "a\u{1f600}b\u{1f600}", "[$&]");
split("", "", "\u{1f600}");
split("\u{1f600}", "", "a\u{1f600}b");
split("x*", "", "a\u{1f600}b");

const results = cases.map((entry) => {
  const re = new RegExp(entry.pattern, entry.flags);
  let expected;
  switch (entry.op) {
    case "test":
      expected = re.test(entry.input);
      break;
    case "search":
      expected = entry.input.search(re);
      break;
    case "split":
      expected = entry.input.split(re, entry.limit);
      break;
    case "replace":
      expected = entry.input.replace(re, entry.replacement);
      break;
    default:
      throw new Error(`unknown op ${entry.op}`);
  }
  return { ...entry, expected };
});

const here = dirname(fileURLToPath(import.meta.url));
const outPath = join(here, "..", "tests", "oracle", "regexp-vectors.json");
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify(results, null, 2) + "\n");
console.log(`wrote ${results.length} vectors to ${outPath}`);
