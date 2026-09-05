# Site Speed Insight

This project is a Streamlit dashboard for understanding website speed in a more practical way than a raw PageSpeed Insights report.

PageSpeed Insights already gives a lot of technical detail, but it can still be hard to answer the questions that usually matter most:

- Is this site actually slow compared to other sites?
- Which Core Web Vital should be looked at first?
- Is the issue mostly loading speed, layout stability, responsiveness, or something else?
- How does the result change when I compare against all sites versus a specific category?

The dashboard adds a benchmarking layer on top of PageSpeed Insights data. A user can run a PSI audit for a URL, then compare the result against a larger dataset of audited websites by device and category.

## What the Dashboard Does

The app currently focuses on the metrics that users and site owners are most likely to care about:

- Largest Contentful Paint (LCP)
- Cumulative Layout Shift (CLS)
- Interaction to Next Paint (INP)
- Performance Score
- First Contentful Paint (FCP)
- Total Blocking Time (TBT)
- Speed Index
- Time to First Byte (TTFB)
- Time to Interactive

Overview separates lab LCP, CLS, and TBT from real-user LCP, CLS, and INP, then explains the results and presents platform-specific recommendations. Benchmarks and supporting metrics are available in Detailed results.

## Main Features

- Run a PageSpeed Insights audit from the dashboard.
- Compare the result against all sites or a selected site category.
- Switch benchmark categories after the audit without rerunning PSI.
- Show Core Web Vitals as the main user-facing metrics.
- Provide a "What to Fix First" section with links to web.dev guides.
- Show detailed benchmark cards for each metric.
- Keep raw audit data available for debugging or deeper review.

## Why I Built It This Way

My original idea was to predict how much faster a website could become. After working with Lighthouse data more, I realized that a more useful problem was benchmarking and prioritization.

A business user does not always need another long technical report. They need to know where to start. This dashboard is meant to turn PSI data into something easier to compare, explain, and act on.

## Data

The dashboard uses audit data stored in `src/dashboard/data`. Each metric has its own benchmark CSV with a similar structure:

```text
metric_value
supporting resource metrics
category
strategy
```

The category data is used so a user can compare a site against all audited sites or against sites in a similar category.

## Project Structure

```text
src/
  dashboard/
    app.py                 Streamlit app entry point
    modules/
      site_tester.py       Dashboard UI and benchmark logic
    utils/
      data_loader.py       Loads metric benchmark datasets
      fetch_lighthouse_data.py
      platform_guidance.py
    data/                  Benchmark CSV files
```

## Run the App

This project is intended to run in a conda environment.

```bash
conda env create -f environment.yml
conda activate site-speed-tracker
streamlit run src/dashboard/app.py
```

If you already have a conda environment for the project, install the dependencies from `environment.yml` and run the same Streamlit command.

## Notes

The dashboard still depends on PageSpeed Insights results, so live audits can vary between runs. That is normal for Lighthouse-style lab data.
