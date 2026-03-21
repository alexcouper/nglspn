# roommate

**URL:** https://github.com/finnure/roommate

## Database Description

Roomselector app to help organize room assignments for a soccer team

## Product Overview

Roommate is a web application built to solve the problem of organizing dormitory assignments for an Icelandic soccer team traveling to tournaments (specifically the IberCup in Portugal). Hotels accommodate three players per room, and rather than assigning rooms arbitrarily, the app lets each player nominate three preferred roommates, guaranteeing a match with at least one of their choices. The system includes an admin dashboard for managing player rosters and distributing selection links, a player-facing selection interface, a verification system using email or SMS, an automated assignment engine that generates optimal room pairings from collected preferences, and CSV export for the final assignments. The tech stack is Django 6.0 with Python 3.14, PostgreSQL for production (SQLite for development), Redis for caching, Celery for async task processing, and Docker Compose for orchestration with Nginx, Gunicorn, and Let's Encrypt SSL via Certbot.

## Possible Categories

- **Sports & Recreation** - Directly serves a soccer team's organizational needs, automating the logistics of player accommodation for tournament travel.
- **Productivity & Utilities** - A focused utility tool that solves a specific organizational problem (room assignment optimization) through preference collection and automated matching.
- **Consumer Products** - A user-facing application where players interact with a selection interface to express their preferences and receive their assignments.
