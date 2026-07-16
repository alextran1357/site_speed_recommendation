# Website Speed Benchmarking and Performance Insights

## Project Overview

This project uses Google Lighthouse/PageSpeed Insights data to analyze website performance and help identify the most important areas for improvement.

Originally, the goal was to predict how much faster a website could become. However, Lighthouse already provides technical recommendations and estimated savings. Because of that, this project was reframed to solve a more practical problem:

> How does a website perform compared to similar websites, and what performance area should be prioritized first?

Instead of replacing Lighthouse, this project builds a data-driven benchmarking layer on top of Lighthouse data. It compares websites against others in the same category and translates technical performance metrics into simpler, more actionable insights.

---

## Problem Statement

Website owners can run Lighthouse and receive a detailed performance report, but the results can be difficult to interpret.

A Lighthouse report may show metrics like:

- Largest Contentful Paint
- Total Blocking Time
- Speed Index
- Cumulative Layout Shift
- JavaScript transfer size
- Image transfer size
- DOM size
- Third-party requests

However, a non-technical user may still not know:

- Is my website actually slow compared to similar websites?
- Which performance issue is the biggest concern?
- Should I focus on JavaScript, images, third-party scripts, or layout issues first?
- Are my Lighthouse results unusually bad or fairly normal for my website category?

This project addresses that gap by turning Lighthouse data into a benchmark and priority guide.

---

## Project Goal

The goal of this project is to create a system that can:

1. Collect Lighthouse performance data for many websites.
2. Organize websites by category and device strategy.
3. Compare an individual website against similar websites.
4. Identify which performance metrics are unusually poor.
5. Recommend the most likely area to investigate first.

---

## Example Output

For a given website, the final tool could produce an output like:

```text
Website: example.com
Category: Local Business
Device: Mobile

Overall Performance:
Worse than 76% of similar websites

Largest Contentful Paint:
Worse than 82% of similar websites

Total Blocking Time:
Worse than 70% of similar websites

Main Performance Issue:
JavaScript

Why:
This site has higher script size, script execution time, and unused JavaScript savings than most similar websites.

Suggested Focus:
Review unused JavaScript, plugins, tracking scripts, and third-party code.
---

## Dashboard App

The completed dashboard lives in `src/dashboard` and is designed as a business-facing LCP benchmarking tool.

### What it does

- Runs a PageSpeed Insights audit for a submitted URL.
- Lets the user benchmark against all sites or the selected website category.
- Shows LCP percentile performance against comparable peers.
- Ranks the most likely performance investigation areas.
- Provides plain-English recommendations for business users.
- Includes a scenario planner that estimates how LCP could change if resource metrics moved toward better peer percentiles.

### Run with conda

```bash
conda env create -f environment.yml
conda activate site-speed-insight
streamlit run src/dashboard/app.py
```

If you already have a conda environment for this project, install the dependencies from `environment.yml` into that environment and run the same Streamlit command.

### Notes

The scenario planner is a model-based planning estimate, not a guaranteed post-optimization PSI result. Use it to prioritize likely improvement areas, then validate real changes with a fresh audit.
