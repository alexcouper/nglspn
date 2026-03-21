# Gasvaktin

**URL:** https://github.com/gasvaktin/gasvaktin

## Database Description

Automated price comparison tool for petrol stations across Iceland, providing up-to-date fuel prices. Running/data collecting since 2016. Code and data published under MIT licence.

## Product Overview

Gasvaktin is an open-source automated fuel price monitoring system that tracks petrol (95 octane) and diesel prices across all major Icelandic petroleum companies: Atlantsolía, Costco Iceland, N1, Olís/ÓB, and Orkan. Built in Python using Selenium with Firefox/geckodriver, the system scrapes pricing data from oil company websites every 15 minutes. When price changes are detected, they are automatically committed to the git repository, creating a comprehensive historical record of fuel prices in Iceland dating back to 2016 with over 14,000 commits.

The data is published as JSON files (both human-readable and minified) and is freely reusable under the MIT licence. The companion website gasvaktin.is allows users to compare current fuel prices and find nearby petrol stations. The project also provides tools for extracting and analyzing historical price trends from the git history, making it a valuable resource for research and consumer awareness around fuel pricing in Iceland.

## Possible Categories

- **Open Data & Transparency** - Provides freely accessible, automatically collected fuel pricing data under an open licence, promoting price transparency in the Icelandic fuel market.
- **Consumer Tools** - A practical price comparison tool that helps consumers find the cheapest fuel near them, saving money on everyday expenses.
- **Community Boosters** - A long-running community resource that benefits all Icelandic drivers by making fuel price information open and accessible.
- **Data & Analytics** - A data collection and analysis project with a rich historical dataset spanning nearly a decade, useful for research and trend analysis.
