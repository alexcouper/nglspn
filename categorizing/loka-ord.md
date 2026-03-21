# Loka-Orð

**URL:** https://github.com/Loknar/loka-ord

## Database Description

Frjálst gagnasafn yfir íslensk orð, beygingamyndir og samsetningu þeirra og fleira, undir frjálsu almenningseignarleyfi (LGPLv3). (A free dataset of Icelandic words, declensions, and compositions under LGPLv3.) Started September 2022 with 13 words, now over 100,000 words and around 1,000 abbreviations.

## Product Overview

Loka-Orð is an open-source Icelandic lexical database containing over 105,000 words, including roughly 76,000 common words (nouns, adjectives, verbs, numerals, pronouns, particles), nearly 30,000 proper nouns (personal names, place names, nicknames), and close to 1,000 abbreviations. All entries include inflected forms (declensions/conjugations) and compound word analysis.

The project is built with Python 3.10+ and uses SQLite for storage. Words are organized as individual JSON files categorized by part of speech and gender, and the repository includes a precompiled search index for fast lookups. A command-line toolkit provides database initialization, word additions via a terminal interface, sentence scanning to identify Icelandic words within text, search across the full corpus, and batch processing for modified entries.

A notable linguistic feature is the use of the Polish letter "Ł" to distinguish words with identical spelling but different pronunciations, supporting precision for speech synthesis and language analysis applications. The project is actively maintained with close to 2,000 commits and is licensed under LGPLv3.

## Possible Categories

- **Language & Data** - A structured linguistic dataset and toolkit for the Icelandic language, fitting squarely into language technology and open data.
- **Dev Tools** - Provides a programmatic CLI and database that developers can integrate into NLP pipelines, spell checkers, or language learning applications.
- **Open Source** - A community-oriented, freely licensed resource built and maintained in the open on GitHub.
- **Society Impact** - Contributes to the preservation and accessibility of the Icelandic language by making a comprehensive word database freely available to anyone.
