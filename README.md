# Ahrefs Domain Rating Checker for Google Sheets

This is a ready-to-install Google Apps Script system for checking domains and URLs in bulk with Ahrefs’ free Domain Rating API endpoint.

It provides:

- one target per row in an `Ahrefs Input` sheet;
- bulk POST requests with up to 1,000 targets per request;
- duplicate removal during the API call while keeping every input row in the result table;
- retry handling for temporary HTTP 429 rate limits;
- status tracking (`RUNNING`, `OK`, `DUPLICATE`, `ERROR`, and `RATE LIMITED`);
- a complete `DR Results` table with input row, target, DR, timestamp, and error details;
- a `Settings` sheet containing the endpoint, attribution, and official documentation links;
- a private API-key setting stored in Google User Properties rather than in a spreadsheet cell;
- a menu and a sidebar for checking pending rows, selected rows, all rows, testing the connection, and replacing the API key.

## Install in Google Sheets

1. Open the Google Sheet that will contain the checker.
2. Open **Extensions → Apps Script**.
3. Replace the default `Code.gs` contents with the contents of `Code.gs` in this package.
4. In the Apps Script editor, click **+ → HTML**, name the file `Sidebar`, and paste in `Sidebar.html`.
5. Open **Project Settings**, enable **Show “appsscript.json” manifest file in editor**, and replace the manifest contents with `appsscript.json` from this package.
6. Save the project. Run `setup` once from the Apps Script editor and approve the requested Google permissions. Then reload the spreadsheet.
7. In the new **Ahrefs DR Checker** menu, choose **Set / replace API key** and paste the Ahrefs APIv3 key.
8. Paste one domain or URL per row in column A of `Ahrefs Input`.
9. Choose **Ahrefs DR Checker → Check pending rows**. The output will appear in `DR Results`.

If the menu does not appear immediately, reload the spreadsheet after saving the script. The first run may take a little longer because Google asks for authorization.

## Input examples

These are valid examples:

```text
example.com
https://example.com/
https://example.com/blog/article
subdomain.example.com
```

Use one domain or URL per row. Do not paste labels, comma-separated descriptions, or multiple targets in one cell. The script preserves the target you entered and sends it to Ahrefs after trimming surrounding whitespace and matching quote marks.

## How to use it

- **Check pending rows** checks rows with a blank status, `PENDING`, `ERROR`, or `RATE LIMITED`. Completed rows are skipped.
- **Recheck selected rows** checks the selected rows on `Ahrefs Input`, including completed rows.
- **Recheck all rows** refreshes every non-empty input row.
- **Test API connection** checks `ahrefs.com` and confirms that the saved key can call the endpoint.
- **Set / replace API key** replaces the key saved for the current Google account.
- **Clear saved API key** removes the key from Google User Properties.

The `DR Results` sheet is rebuilt after every check so it remains a complete table for all non-empty input rows. A row with the same target as an earlier row is labeled `DUPLICATE`, while still receiving the same DR value. This makes it easy to filter or export the table.

## Ahrefs rules and safe-use guidelines

This implementation uses Ahrefs’ **free Domain Rating** endpoint, not the paid Site Explorer or paid Batch Analysis endpoint. Ahrefs’ current reference says the free POST endpoint requires an APIv3 key, accepts up to 1,000 target domains or URLs, and allows the `dr3` or `dr4` version. This script uses `dr3`.

Follow these rules when using the sheet:

1. Keep the required attribution visible wherever DR data is displayed or published: **“Domain Rating by Ahrefs”**, with a functional link to `https://ahrefs.com/`. The `Settings` sheet records this attribution and the results sheet is intended to stay inside the workbook.
2. Use the data for your own internal analysis or another permitted use. Do not repackage, sell, redistribute, or build a competing DR database or product from the data.
3. Do not scrape Ahrefs’ website, rotate keys, bypass rate limits, or attempt to defeat restrictions. This tool calls only the documented API endpoint.
4. Keep the API key private. Do not put it in a cell, share it in a public Apps Script project, or paste it into a chat or public repository. The script stores it in Google User Properties for the user who saves it.
5. Respect the API’s rate limit. Ahrefs documents a default limit of 60 requests per minute and may also throttle dynamically. The script sends at most one request per 1,000 unique targets and retries HTTP 429 responses with backoff, but you should still avoid repeatedly running very large sheets.
6. Check Ahrefs’ current license before publishing or redistributing DR data. Ahrefs can change the endpoint, rate limits, license, or access rules.

The endpoint is free according to the current API reference, but “free” does not mean unrestricted. The API key still identifies the account and Ahrefs can limit or suspend access for misuse.

## Troubleshooting

**`Set an Ahrefs API key first`** — Use **Ahrefs DR Checker → Set / replace API key**. Only workspace owners and admins can create/manage keys in Ahrefs.

**`HTTP 401` or `HTTP 403`** — The key may be invalid, expired, revoked, or not permitted for the endpoint. Create a new key in Ahrefs and replace the saved key.

**`RATE LIMITED`** — Wait and run the pending check again. The script retries 429 responses automatically, but Ahrefs can apply dynamic throttling.

**No result for a row** — Check that the cell contains exactly one domain or URL and no spaces inside the target. Correct the input and run **Recheck selected rows**.

**The sidebar cannot be opened** — Run **Setup / repair sheets**, reload the spreadsheet, and try **Open control panel** again.

## Official references

- [Ahrefs free Domain Rating endpoint](https://docs.ahrefs.com/en/api/reference/public/post-domain-rating-free)
- [Ahrefs API introduction, eligibility, and rate limits](https://docs.ahrefs.com/en/api/docs/introduction)
- [Ahrefs API key creation and usage controls](https://docs.ahrefs.com/en/api/docs/api-keys-creation-and-management)
- [Ahrefs Domain Rating license](https://ahrefs.com/legal/domain-rating-license)
