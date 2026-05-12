# share-doc

Unofficial documentation website for SHARE survey data.

Website: <https://blue-poppy.github.io/share-doc/>

SHARE, the Survey of Health, Ageing and Retirement in Europe, is a
cross-national panel survey covering health, socio-economic status, family
networks, work, retirement, and ageing. This project turns local SHARE release
metadata into a browsable documentation site focused on practical dataset use:
which files exist, what each module contains, how modules are named, and which
variables are available by wave.

## What this site is for

- Finding the right SHARE module before loading data in analysis code.
- Looking up variable labels, storage types, and formats by wave and dataset.
- Checking whether a dataset is respondent-level, country-level, interviewer
  level, or repeated within respondent.
- Understanding naming differences between official SHARE module labels,
  downloaded `.dta` filenames, and `pyshare` module names.
- Spotting wave-specific caveats, especially SHARELIFE modules in wave 3 and
  generated `gv_` datasets.

The site is intended as a local companion to the official SHARE documentation,
not a replacement for it. Use the official SHARE documentation for questionnaire
wording, routing details, release notes, citation requirements, and cross-wave
harmonisation.

## Contents

- <https://blue-poppy.github.io/share-doc/> is the website landing page.
- <https://blue-poppy.github.io/share-doc/guides/modules/> explains how to
  choose and name SHARE modules.
- <https://blue-poppy.github.io/share-doc/guides/> summarizes the generated
  variable dictionary.
- <https://blue-poppy.github.io/share-doc/guides/wave-9/> is an example
  wave-specific variable page.

