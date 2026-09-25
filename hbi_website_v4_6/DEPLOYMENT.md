# HBI Directories v4 deployment

- GitHub repository: `dslsotolp/HBI_Directories_V2`
- Streamlit entry point: `hbi_website_v4_6/Home.py`
- Git branch: `streamlit-v4`
- Python: `3.13`
- Python dependencies: `hbi_website_v4_6/requirements.txt`
- Cloud configuration: `.streamlit/config.toml`
- Requested app subdomain: `hbi-directoriesv4`
- Intended public app URL: `https://hbi-directoriesv4.streamlit.app/` (pending cloud creation)

The existing v2 and v3 deployments remain on `main` and `streamlit-v3`.
This release uses an isolated deployment checkout under `.deploy/streamlit-v4`.
The package includes the current public website, its production data, and portraits.
Crawler code, credentials, raw crawls, staged batches, backups and local browser
profiles are excluded. Dependencies are pinned to the versions validated locally.

Create a new app in Streamlit Community Cloud using the repository, branch and
entry point above, and set the custom subdomain to `hbi-directoriesv4` if available.
Use Advanced settings to select Python 3.13. No app secrets are needed.
