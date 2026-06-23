# Design Document: Authority Contribution Scraper

## Overview

The Authority Contribution Scraper is a tool designed to gather and store contributions that contribute to Xebia's
authority mission. It scrapes data from various sources such as blog posts, GitHub Pull Requests, and XKE (Xebia
Knowledge Exchange) sessions, and stores them in Google BigQuery for further analysis and reporting.

## Architecture

The system is built as a Python Flask application that can be triggered via HTTP. It follows a modular architecture
consisting of several key components:

### 1. Flask Application (`app.py`)

Provides the external interface for the scraper.

- `/scrape`: Triggers the loading process.
- `/graph/contributions-per-month`: Generates a visual report of contributions.

### 2. Loader (`loader.py`)

The orchestrator or "playmaker" of the system. It initializes the `Sink` and all registered `AuthoritySource`
implementations, then iterates through each source to fetch and store data.

### 3. Sources (`src/authority/sources/`)

Modular scraper implementations for different platforms.

- **Base Class (`AuthoritySource`)**: Defines the interface for all sources. It uses a registry pattern (via
  `AuthoritySourceFactory`) to automatically register subclasses.
- **Implementations**:
    - `BlogSource`: Scrapes WordPress posts from xebia.com.
    - `GitHubPullRequestSource`: Scrapes PRs from GitHub.
    - `XKESource`: Scrapes session data from the XKE platform.
    - `AttendeesSource`: Scrapes attendance data.

### 4. Sink (`sink.py`)

Handles data persistence for contributions.

- Primarily interacts with **Google BigQuery**.
- Manages table creation and row insertion.
- Provides methods to query for the "latest" entries to support incremental scraping (avoiding duplicates).

### 5. Contributor Synchronization (`src/authority/model/contributor.py`)

Ensures that all authors of contributions are tracked in a separate `contributors` table.

- `Synchronizer`: Automatically identifies new authors in the `contributions` table and fetches their organizational
  unit (e.g., Cloud, Data, etc.) using the Microsoft Graph API.

### 6. Reporting (`report.py`)

Generates reports and visualizations based on the scraped data.

- Can generate PNG graphs of contributions per month.
- Provides CLI tools to print summaries of authors and repositories.

### 7. Dinner Registration Synchronizer (`dinner_registration_synchronizer.py`)

A specialized synchronizer that reads from a Firestore database (`xke-nxt`) and writes aggregated dinner registration
data to BigQuery.

### 8. Data Model (`src/authority/model/`)

Standardizes data formats.

- `Contribution`: Represents a single contribution (blog, PR, etc.).
- `Contributor`: Represents an author and their unit.

## Data Flow

1. A trigger (e.g., Cloud Scheduler) calls the `/scrape` endpoint.
2. The `Loader` is invoked.
3. For each registered `AuthoritySource`:
   a. The source queries the `Sink` for the date of the latest stored contribution for its type.
   b. The source fetches new contributions since that date from its respective API (WordPress, GitHub, etc.).
   c. New contributions are yielded back to the `Loader`.
4. The `Loader` passes these contributions to the `Sink`.
5. The `Sink` batches and inserts the rows into BigQuery.

## Infrastructure & Deployment

- **Platform**: Google Cloud Run.
- **Trigger**: Google Cloud Scheduler (hourly).
- **Storage**: Google BigQuery.
- **Deployment**: Automated via Cloud Build triggered by version bumps and git tags.
- **Infrastructure as Code**: Managed via Terraform.

## Configuration & Secrets

- **Secrets**: Managed via Google Secret Manager.
- **Utilities**:
    - `lazy_env`: A helper to retrieve configuration from environment variables, falling back to Secret Manager (using
      `gsm://` prefix) or 1Password (using `op://` prefix) if necessary.
    - `SecretManager`: A wrapper for the Google Secret Manager API.
