# Dashboard

This note is meant to be rendered with the `Dataview` Obsidian community plugin.

## Source Pages

```dataview
TABLE year AS Year, lead_author AS "Lead Author", source_kind AS Kind, page_count AS Pages, length(concepts) AS Concepts
FROM "wiki/sources"
WHERE note_type = "source"
SORT year DESC, file.name ASC
```

## Concept Pages

```dataview
TABLE concept_group AS Group, source_count AS Sources, related AS Related
FROM "wiki/concepts"
WHERE note_type = "concept"
SORT source_count DESC, file.name ASC
```

## Recently Converted PDFs

```dataview
TABLE year AS Year, page_count AS Pages, conversion_pipeline AS Pipeline
FROM "_meta/converted_sources"
WHERE note_type = "source_cache"
SORT converted_at DESC
```

## Recently Filed Notes

```dataview
TABLE generated_at AS Generated, context_mode AS Context
FROM "wiki/derived"
SORT generated_at DESC
```
