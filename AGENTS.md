# AGENTS.md

## Project
Build a guided reading system for AI/AIGC research blogs.

## Goal
Help the user systematically finish a curated set of blogs and keep up with updates.
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

## MVP rules
- Keep v1 single-user only
- No auth in v1
- RSS first, scraping later
- Keep UI clean and minimal
- Use deterministic scheduling rules
- Use OpenAI API only for:
  - article analysis
  - weekly plan generation
  - review question generation

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
- Add seed data for demo blog sources
- Run lint after major changes
- Update README when setup changes
