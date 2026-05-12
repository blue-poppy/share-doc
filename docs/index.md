---
icon: lucide/house
---

# SHARE Survey Documentation

This website is a practical reference for working with SHARE survey release
files. It documents the SHARE datasets by wave, module, and variable so
that analysts can find the right files faster and use them more consistently in
research workflows.

SHARE is the Survey of Health, Ageing and Retirement in Europe. It follows older
adults across countries and waves, with data on health, family, employment,
income, assets, housing, social networks, retirement, and end-of-life interviews.

## What You Can Use It For

- Choose which SHARE modules to load for a research question.
- Translate between official module labels, downloaded `.dta` filenames, and
  `pyshare` module names.
- Look up variable names and labels within a specific wave.
- Check basic dataset structure, including row counts, key hints, and whether a
  module is respondent-level, country-level, interviewer-level, or repeated.
- Identify generated `gv_` datasets that may already contain harmonised or
  derived variables.
- Avoid common wave-specific mistakes, especially around SHARELIFE modules in
  wave 3.

## Start Here

- [Choosing SHARE modules](guides/modules.md) explains module names, filename
  patterns, and common starting points for analysis.
- [Variable dictionary](guides/index.md) lists the available waves and links to
  wave-specific variable pages.

## Scope

This is an unofficial local documentation site. It is designed to make everyday
data discovery easier, especially when preparing analysis code or checking which
variables are available in a release.

It does not replace the official SHARE documentation. For questionnaire wording,
routing, release notes, citations, and cross-wave item harmonisation, use the
official SHARE resources:

- SHARE Data Documentation: <https://share-eric.eu/data/data-documentation>
- SHARE Data & Documentation Tool: <https://www.share-datadocutool.org/>
- SHARE Cross-Wave Comparison:
  <https://share-eric.eu/data/data-documentation/questionnaires/cross-wave-comparison>
