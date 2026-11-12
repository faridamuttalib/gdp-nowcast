# Your web dashboard is ready

## Try it on this computer

Double-click **START_DASHBOARD.cmd**. It opens the dashboard in your browser. Keep the small server window open while using the app; close it or press Ctrl+C when finished.

Choose your quarter, date cutoff and stage. Start with **Auto**. The yellow **Update data** button downloads the public indicators and recalculates the model. Source tables and units are under **Data explorer**; equations are under **Methodology**. **Sector lab** contains the baseline fits and separate what-if sliders.

No Excel, VBA import or API key is needed. The launcher uses this computer's Codex Python runtime where available; on another machine, install Python 3.10+ first.

## Put it on GitHub

1. Create a repository and upload this folder's contents, including `.github`, to its `main` branch.
2. In repository **Settings → Pages**, choose **GitHub Actions** as the publishing source.
3. Open **Actions → Update data and publish dashboard → Run workflow**.
4. Once deployed, open the URL GitHub provides.

After setup, the included workflow refreshes official sources on weekdays at **1:30 pm Malaysia time**. GitHub can delay scheduled runs. On the hosted dashboard, **Update data** directs you to run the authenticated GitHub workflow, then check for the new published snapshot. The local dashboard performs the download directly with one click.

The GitHub workflow is prepared but has not been run against your account. No repository was created or published. Full setup, source definitions and limitations are in **README.md**.
