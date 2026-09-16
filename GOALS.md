# Project Goals

## Primary problem

The project addresses three recurring workflows that currently require separate tools:

1. Converting PDFs into useful Markdown.
2. Reading and writing Markdown comfortably.
3. Maintaining a portable personal knowledge base with links, backlinks and a graph.

The solution should unify those workflows without turning the user's notes into proprietary application data.

## Product goal

Build a simple, local-first Markdown workspace that can:

- open and edit an isolated `.md` file immediately;
- render rich Markdown extensions;
- open any directory as a portable knowledge workspace;
- discover links and relationships between notes;
- visualize those relationships;
- run optional operators such as PDF → Markdown;
- prepare high-quality Markdown for later AI workflows.

## Success conditions for the first stable release

A user can:

- double-click/open a `.md` file and edit it;
- see a synchronized or near-real-time preview;
- render GFM-like Markdown, math and Mermaid diagrams;
- open a directory containing ordinary Markdown files;
- navigate files without importing them into a proprietary database;
- use `[[wikilinks]]`, backlinks and tags;
- view and navigate a 2D graph;
- convert representative native and scanned PDFs to Markdown;
- keep extracted assets in predictable relative directories;
- move the workspace to another computer and reopen it;
- rebuild indexes if generated application state is deleted.

## Non-goals for the initial product

The first stable release does not need:

- cloud synchronization service owned by this project;
- user accounts;
- collaboration server;
- mobile application;
- graph 3D;
- autonomous AI agents;
- mandatory embeddings;
- built-in vector database;
- full Obsidian plugin compatibility;
- browser extension;
- WYSIWYG parity with office suites;
- support for every document import format.

## Long-term direction

Evolve from a Markdown workspace into a **Markdown Operator environment** where deterministic tools and optional AI operators can inspect, transform, relate and prepare knowledge while keeping Markdown files sovereign.
