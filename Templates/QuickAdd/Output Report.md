---
title: "{{VALUE:title|label:Report title}}"
aliases: []
note_type: "output_report"
report_type: "{{VALUE:report_type|default:memo|label:Report type}}"
audience: "{{VALUE:audience|label:Audience}}"
created: "{{DATE:YYYY-MM-DD}}"
sources: []
tags:
  - "output"
  - "report"
---

# {{VALUE:title|label:Report title}}

## Brief
{{VALUE:brief|label:One-line brief}}

## Findings
<% tp.file.cursor(1) %>

## Open Questions

## References
