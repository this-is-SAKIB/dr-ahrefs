# Standalone Ahrefs DR Checker

This package gives you four ways to use the checker:

1. `index.html`: open it locally in a browser or upload it to GitHub Pages. It is a static frontend with CSV download.
2. `run_local.py`: serve the HTML locally with a localhost-only proxy. This is the recommended browser method because it avoids CORS and automatically uses `ahrefs_local_key.txt`.
3. `ahrefs_dr.py`: run the checker directly from a terminal. It can accept pasted links interactively and print a compact table.
4. The existing Google Apps Script files remain available if you later decide to use a Google Sheet menu/sidebar workflow.

## Option A — offline HTML or free static hosting

Double-click `index.html`, or open it in a browser. Paste one domain or URL per line, enter your Ahrefs APIv3 key, and click **Check DR**. You can also load a `.txt`, `.csv`, or `.tsv` file. Use **Download CSV** after the check.

The page does not save the API key to local storage. It lives only in the current browser tab. The page includes the required clickable attribution: **Domain Rating by Ahrefs**.

### Recommended browser method: localhost mode

Open a terminal in the folder containing `index.html`, `run_local.py`, and `ahrefs_dr.py`, then run:

```powershell
python run_local.py
```

Open the `http://127.0.0.1:8765/index.html` address printed in the terminal and click **Check DR**. The local proxy automatically reads `ahrefs_local_key.txt` and does not ask for the key in the browser. Stop it with `Ctrl+C`.

`ahrefs_local_key.txt` is excluded by `.gitignore`. Do not upload it to GitHub. If you delete it, set `AHREFS_API_KEY` before starting the local server.

This is the fix for the common situation where the HTML page displays correctly but shows no actual results: Ahrefs’ API response does not include the browser CORS headers needed by a `file://` page or GitHub Pages page to call it directly.

### GitHub Pages

1. Create a GitHub repository.
2. Upload `index.html` as the repository’s `index.html`.
3. Open **Settings → Pages** and publish the main branch.
4. Open the generated Pages URL and enter your own API key when using it.

Do not put an API key inside the HTML source or repository. Anyone who can view the page source would be able to copy it.

### Blogger

You can copy the contents of `index.html` into a Blogger HTML/JavaScript gadget or an HTML page if your Blogger theme permits inline scripts. Blogger may sanitize or restrict scripts depending on the editor and theme. If the page does not run there, use GitHub Pages or the terminal version.

### Browser CORS limitation

The static page calls Ahrefs directly from the browser when opened as a file or hosted on GitHub Pages. If the browser reports a CORS/network error, this is a browser security restriction rather than a bad DR request. A static GitHub Pages or Blogger page cannot safely act as a secret API proxy. Use `run_local.py` for a browser UI, or use the terminal runner below.

## Browser appearance and columns

The localhost page starts in night mode. Use **Switch to light mode** if needed.

The results table starts with only these columns visible:

- Row
- Input
- Domain Rating

Use **Show / hide columns** to enable `Normalized Target`, `Status`, `Checked At (UTC)`, `Ahrefs Target`, or `Error`. The CSV download always includes all detailed columns, regardless of what is visible in the browser.

## Option B — terminal runner

The Python script uses only the Python standard library. Python 3.9 or newer is recommended.

### Paste links interactively

Run the script without an input filename:

```powershell
python ahrefs_dr.py
```

Paste one domain or URL per line, then press **Enter on an empty line**. The script prints a compact table directly in the terminal with `Row`, `Input`, `Status`, `Domain Rating`, and `Error` columns.

### 1. Put targets in a text file

Create `urls.txt` with one target per line:

```text
example.com
https://example.org/page
subdomain.example.net
```

### 2. Set the API key securely

PowerShell:

```powershell
$env:AHREFS_API_KEY = "paste-your-key-here"
```

macOS/Linux:

```bash
export AHREFS_API_KEY="paste-your-key-here"
```

You can omit this step and let the script ask for the key privately when running interactively.

### 3. Run the checker

```bash
python ahrefs_dr.py urls.txt --output ahrefs_dr_results.csv
```

The compact table is printed in the terminal. When `--output` is supplied, the detailed table-shaped CSV is also saved with:

- original input;
- normalized target;
- status;
- Domain Rating;
- UTC timestamp;
- Ahrefs’ returned target;
- error details where applicable.

If you do not supply `--output`, no file is written.

### CSV/TSV input

Read the first column of a CSV:

```bash
python ahrefs_dr.py domains.csv --output results.csv
```

Read the second column:

```bash
python ahrefs_dr.py domains.csv --column 2 --output results.csv
```

Read a TSV:

```bash
python ahrefs_dr.py domains.tsv --output results.csv
```

Read from standard input:

```powershell
Get-Content urls.txt | python ahrefs_dr.py - --output results.csv
```

Use the newer DR version if required by your workflow:

```bash
python ahrefs_dr.py urls.txt --version dr4 --output results.csv
```

## Status meanings

- `OK`: Ahrefs returned a DR value.
- `DUPLICATE`: the same target appeared earlier; its result is copied to this row without another API lookup.
- `INVALID`: the row is blank or contains spaces inside the target.
- `ERROR`: the request failed or Ahrefs returned no result.
- `RATE LIMITED`: Ahrefs continued returning HTTP 429 after the built-in retries.

## Ahrefs rules to follow

The current free Domain Rating endpoint accepts up to 1,000 targets per POST request, requires an APIv3 key, supports `dr3` and `dr4`, and requires attribution. The tools use batches of up to 1,000 unique targets and print or display the attribution near the results.

Ahrefs documents a default limit of 60 requests per minute and may apply additional dynamic throttling. Both tools retry HTTP 429 responses, but do not repeatedly rerun the same large list unnecessarily.

Do not expose your key, rotate keys to bypass limits, scrape the Ahrefs website, or use the output to compile a competing DR database or redistribute DR data as a competing product. Review the license before publishing or sharing results.

Official references:

- [Free Domain Rating API endpoint](https://docs.ahrefs.com/en/api/reference/public/post-domain-rating-free)
- [API introduction and rate limits](https://docs.ahrefs.com/en/api/docs/introduction)
- [API key creation and usage controls](https://docs.ahrefs.com/en/api/docs/api-keys-creation-and-management)
- [Domain Rating license](https://ahrefs.com/legal/domain-rating-license)
