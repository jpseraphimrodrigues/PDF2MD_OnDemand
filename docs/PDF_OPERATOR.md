# PDF to Markdown Operator

## 1. Role

PDF conversion is an optional ingestion tool.

It must not leak conversion-engine concepts into the Markdown editor or workspace domain.

## 2. User goal

Given a PDF, produce useful Markdown and associated assets with minimal manual cleanup.

## 3. Document classes

The operator must be evaluated against:

- native/digital PDF;
- scanned PDF;
- hybrid PDF;
- multi-column academic paper;
- document with tables;
- document with mathematical expressions;
- document with diagrams/images;
- scanned book pages.

Do not classify the entire PDF as only "digital" or "scan" when page-level behavior differs.

## 4. Initial engine strategy

Use one primary production engine first.

Current preferred candidate: Docling behind an adapter.

Alternative engines should be introduced only when measured fixtures expose a real deficiency that justifies the added maintenance/licensing complexity.

## 5. OCR

OCR should be used when required, not indiscriminately on high-quality native text.

The conversion layer may rely on the engine's page/region strategy.

## 6. Asset policy

Default output proposal:

```text
paper.md
paper.assets/
├── p001-img001.png
├── p003-img001.png
└── ...
```

Markdown references use relative paths.

Workspace mode may optionally route assets to a configured workspace asset directory.

## 7. Output

Minimum output:

- `.md`;
- extracted/generated image assets when applicable;
- conversion report/log visible to the user.

Potential report fields:

- engine used;
- OCR used/pages;
- warnings;
- unsupported content;
- output files;
- elapsed processing information.

## 8. Quality strategy

Maintain a golden fixture set rather than relying on subjective one-off inspection.

Representative test corpus should cover the document classes listed above.

The goal is not pixel-identical reproduction.
The goal is structurally useful Markdown.

## 9. Failure policy

A partial conversion must report missing/failed portions.

Do not silently emit apparently successful Markdown after severe extraction failure.

The original PDF is never modified.
