# AGENTS.md

## Project
Build a generic guided reading system for RSS-driven reading workflows.

## Goal
Help users turn a set of blogs or feeds into a finishable curriculum, keep progress moving, and review what they learned.
This is not a preference-based recommender.
This is a curriculum + progress + review system.

## Stack
- Next.js
- TypeScript
- Tailwind CSS
- FastAPI
- SQLModel
- SQLite

## Core entities
- Source
- Article
- Tag
- ArticleRelation
- ReadingLog
- WeeklyReview
- ImportJob
- ImportJobItem

## MVP rules
- Keep v1 single-user only
- No auth in v1
- RSS first, scraping later
- Keep UI clean and minimal
- Use deterministic scheduling rules for Today
- Keep Weekly generation optional and provider-backed
- Support OpenAI-compatible providers via configurable `base_url + api_key + model`

## Reading stages
- foundation
- core
- frontier
- update

## Reading statuses
- planned
- skimmed
- deep_read
- reviewed
- mastered

## Engineering rules
- Prefer small, readable components
- Add loading, empty, and error states
- Keep database schema explicit
- Add seed data for demo sources
- Run lint/tests after major changes
- Update README when setup changes
