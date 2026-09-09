# Site Speed Insight

**Understand what is slowing down your website, what to look at first, and how to get help fixing it.**

Site Speed Insight is a Python and Streamlit application for website owners who may not have a technical background. It turns Google PageSpeed Insights results into readable explanations, prioritized recommendations, and requests that owners can send to a developer or website provider.

The goal is to close the gap between seeing a performance score and knowing what to do next. Technical evidence stays available, but owners should not need to understand Lighthouse terminology to get started.

## Why this project exists

Performance reports contain useful measurements, but interpreting them can be difficult. A website owner still needs to answer:

- What does this problem mean for visitors?
- Which problem should I investigate first?
- What part of the page should I look at?
- Can I make a change myself, or should I contact someone?
- What information should I send that person?

This project is informed by experience working on a site speed team. It aims to provide practical guidance without overwhelming the owner or pretending that a slow measurement proves a particular cause.

## What works today

### Audit and understand a page

Enter a URL and choose mobile or desktop to run a PageSpeed Insights audit. The overview separates:

- **Lab results:** LCP, CLS, and TBT from a simulated Lighthouse test.
- **Real-user results:** LCP, CLS, and INP from CrUX data returned by PageSpeed Insights, when available.

The report explains missing measurements and distinguishes page-level real-user data from website-wide origin fallback. A short interpretation summarizes what the available results mean.

### Find a starting point

The recommendation cards describe loading, movement, and responsiveness problems in plain language. Above-target Core Web Vitals—LCP, CLS, and INP—rank ahead of TBT. Within that group, the ranking considers page-level real-user evidence, severity, source, and distance above the target.

When the audit supplies relevant details, cards can identify:

- The image, text, or video reported as the main content for LCP.
- An image with estimated download savings.
- A stylesheet or script delaying page display.
- A script with reported processing work or unused code.
- An element observed moving during the test.

Recognizable text helps owners locate content. Technical identifiers and longer details remain available in the help request. An affected element is an investigation lead, not automatically the cause of the problem.

### Take action or ask for help

Recommendations include brief actions or things to watch for, with guidance for WordPress, Shopify, Wix, Squarespace, and other or unknown platforms.

Each problem has a **Copy request for help** section containing the page, test device, observed measurements, available element or resource details, and suggested technical checks. It asks the helper to confirm the cause and report the changes and before-and-after results.

### Explore supporting evidence

Detailed results include benchmark comparisons against the bundled audit dataset, by device and site category. Changing the comparison does not rerun the audit. Supporting metrics and extracted audit fields are also available for deeper review.

These benchmarks describe the included dataset, not every website on the internet.

## How it works

1. Request an audit through the Google PageSpeed Insights API.
2. Extract and validate Lighthouse measurements, real-user data, and item-level findings.
3. Compare available measurements with thresholds and the bundled benchmark data.
4. Select relevant investigations and display owner guidance and developer help requests.

**The current dashboard uses explicit rules, not an AI model, to generate its recommendations.** It does not modify the audited website.

## Technology and data

| Area | Tools and purpose |
| --- | --- |
| Application | Python, Streamlit |
| Audit collection | Google PageSpeed Insights API, Lighthouse, CrUX data returned through PSI, Requests |
| Data processing and benchmarking | pandas, NumPy, JSON, CSV |
| Website collection | Beautiful Soup, Requests, cached desktop and mobile audits |
| Historical data workflows | Databricks, Spark SQL, workspace tables and volumes, Jupyter notebooks |
| Modeling experiments | scikit-learn, XGBoost, joblib, Ax, matplotlib, seaborn |
| Regression checks | Python unittest, mocks, Streamlit AppTest |

Benchmark CSV files are stored in `src/dashboard/data`. Collection and analysis code is included separately from the application.

## Roadmap

The roadmap distinguishes validating the current product from expanding its scope. These items are future work, not existing features or release commitments.

### Next: validate the MVP

- Test complete reports across representative websites, platforms, and devices.
- Check whether nontechnical owners can identify a useful next action and use the help request.
- Fix reproducible recommendation or display problems, and improve setup and failure recovery where needed.

### After validation: help owners follow through

- Add a session-level before-and-after retest for the same page and device.
- Expand platform walkthroughs where users repeatedly get stuck.
- Offer a combined shareable report if per-problem help requests are insufficient.

### Optional: broader diagnostics

Add more specific checks for image dimensions, image loading behavior, caching, minification, fonts, critical CSS, and third-party scripts when the audit supports them and user feedback justifies the extra complexity. Comprehensive optimization coverage is not required for the MVP.

### Future AI and predictive models

Earlier work explored predicting LCP and understanding performance patterns using regression, tree-based models, XGBoost, and clustering. The repository retains modeling notebooks and a legacy prediction helper and model artifact, but they are not used by the current dashboard.

A future direction is to revisit this work to:

- Estimate expected performance from page characteristics.
- Identify patterns among similar pages that could support investigations.
- Explore estimated improvement scenarios, with clear uncertainty and limitations.

Before returning models to the product, they should be evaluated on representative held-out data and demonstrate useful value beyond the existing rules. Predicting a metric is not proof that changing a feature will cause the predicted improvement. Claims about optimization benefits would need validation against actual before-and-after changes.

### Longer-term possibilities

Saved audit history, monitoring, multiple-page audits, better identification of responsible themes or providers, and collaboration features can follow if there is demand.

**Direct CrUX integration remains deferred.** Revisit it if the existing PSI field-data integration actually breaks. A single page lacking sufficient real-user coverage is not evidence of an integration failure.

## Run locally

Run these commands from the project root:

```bash
conda env create -f environment.yml
conda activate site-speed-tracker
python -m pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` with your Google PageSpeed Insights API key:

```toml
API_KEY = "your-pagespeed-insights-api-key"
```

This file is excluded from version control. The dashboard reads this Streamlit secret; the standalone collection scripts use their own configuration described below.

Start the application:

```bash
streamlit run src/dashboard/app.py
```

Live audits require network access and an API key configured for PageSpeed Insights.

## Run checks

```bash
python -m unittest discover -s tests
```

The suite covers extraction, missing and malformed data, recommendation ranking, owner guidance, help requests, dashboard rendering, and collection behavior. API requests in these checks are mocked; passing tests do not establish that a live API or Databricks workspace is available.

## Repository structure

```text
src/
  dashboard/
    app.py                       Application entry point
    modules/site_tester.py       Report rendering, benchmarks, and recommendation rules
    utils/
      fetch_lighthouse_data.py   PSI requests and measurement extraction
      audit_evidence.py          Validated element and resource findings
      platform_guidance.py       Owner instructions, helper contacts, and guide links
      data_loader.py             Benchmark dataset loading
      predict.py                 Legacy prediction helper; not used by the dashboard
    data/                        Benchmark CSV files
    models/                      Legacy model artifact
  data_collection/               URL crawler, shared batch collector, CSV extraction
  data_manipulation/             Historical data preparation and exploration notebooks
  modeling/                      Historical machine-learning experiments
tests/                          Regression checks
```

## Collection scripts and notebooks

The desktop and mobile entry points in `src/data_collection` share a batch collector and retain separate cache and output paths. In Databricks, the entry points read the configured secret. Elsewhere, set `API_KEY` or pass `api_key` to `run_batch`. Pass `volume_path` to use a different data directory. Importing a collection module does not start a crawl or batch job.

The notebooks are historical Databricks experiments that depend on workspace data and execution context. They are not part of dashboard startup or the regression suite. Some cells overwrite datasets or trained models; they are not a prerequisite for running the app.

## Interpreting results

- Lab measurements vary between runs and may differ from actual visitor experiences.
- Real-user results reflect an aggregated period, typically the previous 28 days, and do not immediately reflect a new change.
- Missing data is not a passing result. Website-wide data does not establish the experience on one specific page.
- Estimated savings and reported moving elements help guide an investigation; they do not guarantee a fix or establish its cause.
- TBT is a lab diagnostic, not a measured real-user INP result.
