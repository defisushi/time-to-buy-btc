

# BTC Regime Tracker — Mobile Web App

## Overview
A mobile-first Bitcoin regime tracking dashboard that helps you assess market conditions across 15 weighted on-chain and macro indicators, organized into 4 phases.

## What We'll Build

### 1. Core Tracker Page
- Integrate your existing BTC Regime Tracker component as the main (and only) page
- Dark theme (slate-950 gradient background) optimized for mobile viewing
- Sticky header with app title and reset button
- Hero signal card showing total weighted score and regime label (High Conviction Long → Risk Off)

### 2. 4-Phase Indicator System
- **Phase 1: Macro Backdrop** — Global M2, Financial Conditions Index
- **Phase 2: Deep Value Zone** — MVRV Z-Score, Realized Price, 200W MA, Reserve Risk, Puell Multiple, Ahr999
- **Phase 3: Capitulation Exhaustion** — Hash Ribbons, SOPR, LTH Supply, Realized Cap RoC
- **Phase 4: Confirmation** — Weekly Higher Low, Stablecoin Supply, Halving Cycle Position
- Each phase collapsible with score summary
- Each indicator expandable with bullish/bearish conditions, explanation, and source info

### 3. Indicator Status Controls
- Tap any indicator to expand it and set status: Bullish / Neutral / Bearish
- Color-coded status dots (green/amber/red) for quick scanning
- Weight multipliers displayed (×1, ×2, ×3)

### 4. Scoring & Persistence
- Weighted score calculation across all 15 indicators
- 5-level regime signal: High Conviction Long, Accumulation Zone, Neutral/Wait, Caution, Risk Off
- All selections saved to localStorage with last-updated timestamp
- Reset button to clear all data

### 5. Reference Guide
- "How to Use This" section with weekly workflow
- Weight system explanation
- High conviction entry criteria

