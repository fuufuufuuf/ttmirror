---
version: 1
name: TikTok Shop - Add Product to Showcase
app: Google Chrome (via chrome-devtools MCP)
tags: ["chrome", "tiktok-shop", "showcase"]
params:
  - name: PRODUCT_ID
    description: "TikTok Shop product ID — used to build the product link"
    required: true
  - name: POST_ACCOUNT
    description: "TikTok username (matches the project Chrome profile folder under chrome_profile/)"
    required: true
---

Add a product (by `PRODUCT_ID`) to the showcase of `${POST_ACCOUNT}`'s TikTok Shop streamer dashboard. The caller (auto_upload.py) has already launched a debug Chrome on `localhost:9222` with the matching profile.

## Rules

- Find element `uid` values via `take_snapshot` (a11y tree). Never estimate pixel coords.
- Prefer `click(..., includeSnapshot=true)` so each click returns the post-state — saves a separate `take_snapshot` call.
- Reuse uids across consecutive steps when the DOM hasn't been re-rendered (`fill` only changes input value; clicks open dialogs / re-render). Re-snapshot only after a real DOM change.
- Sleep 5s after clicking the in-dialog "商品链接" button — the fetch is async and there is no text wait_for that distinguishes success vs. non-affiliate.

## Steps

### Part 1: Reach the showcase product list

1. `list_pages`. If empty, stop: "Debug Chrome on port 9222 is not running."
2. If a page already shows `shop.tiktok.com/streamer/showcase/product/list`, `select_page` it. Otherwise `navigate_page` (type=url) the selected page to that URL.
3. `wait_for` text `["添加商品", "Add product"]`, timeout 15000.

### Part 2: Open the Add Product dialog (and sanity-check account)

4. `take_snapshot` — find the page-level `button "添加商品"` (the one alongside the `"搜索商品"` textbox), and capture `"商品橱窗共有 N 件商品"` (record N as `before_count`).
5. From the same snapshot, verify a `StaticText` near the top matches `${POST_ACCOUNT}` (loose: lowercase + alnum only on both sides). If mismatch, stop: "Chrome profile is logged in as a different account — expected ${POST_ACCOUNT}".
6. `click` the page-level `button "添加商品"` with `includeSnapshot=true`. From the returned snapshot, capture uids of:
   - dialog textbox (placeholder contains `"请在此处输入商品链接"`) → call it **`T`**
   - dialog `button "商品链接"` inside `tabpanel "商品链接"` (NOT the tab) → **`L`**
   - dialog `button "取消"` → **`C`**

### Part 3: Fill, fetch, decide

7. `fill T` with `https://shop.tiktok.com/view/product/${PRODUCT_ID}?region=US`.
8. `click L`.
9. `Bash sleep 5`.
10. `take_snapshot` to find the dialog's submit `button "添加商品"` (alongside `C`, NOT the page-level button). Capture its uid as **`S`**. Then use `evaluate_script` to check the button's real DOM `disabled` property directly — this avoids a11y tree ambiguity around the `disabled` attribute:

    ```js
    () => {
      // Find the submit "添加商品" button inside the dialog (not the page-level one).
      // It is siblings with the "取消" button (C). Filter to visible buttons only.
      const allButtons = [...document.querySelectorAll('button')];
      const dialogButtons = allButtons.filter(b => {
        const text = (b.textContent || '').trim();
        return text.includes('添加商品') && b.offsetParent !== null && b.getAttribute('aria-disabled') !== 'true';
      });
      // The dialog submit is the one with '添加商品' text that is NOT the page-level toolbar button.
      // Prefer buttons whose ancestor includes a dialog/tabpanel role.
      const submitBtn = dialogButtons.find(b => {
        const rect = b.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      }) || dialogButtons[0];
      if (!submitBtn) return { found: false };
      return { found: true, disabled: submitBtn.disabled, text: submitBtn.textContent.trim() };
    }
    ```

    - **`disabled: true`** → product is NOT in the affiliate program. `click C` to close the dialog, then **stop the entire skill** and emit this exact final line:

      `NON_AFFILIATE_PRODUCT: 此商品不是联盟营销商品。请联系卖家，以将其注册到联盟计划中`

    - **`disabled: false`** or `found: false`** → continue. Proceed to Step 11.

### Part 4: Submit, close, and verify by PRODUCT_ID

11. `click S` to submit. The dialog stays open after success.
12. `click C` (or the top-right `×`) to close the dialog. `take_snapshot` and confirm `tabpanel "商品链接"` is gone — this guarantees the next `evaluate_script` runs against the showcase list DOM, not the dialog.
13. Verify the product is in the showcase. Run `evaluate_script` with this exact function (replace `${PRODUCT_ID}` with the real id before submitting the call). The check scans the **entire showcase page DOM** (HTML attributes, text, etc.) for the literal PRODUCT_ID string — TikTok Shop's showcase rows do NOT use `<a href>` links to the product page, so a href-only scan would always return 0 and false-fail. A 19-digit numeric product id is unique enough that any occurrence anywhere on the page is a valid signal:

    ```js
    () => {
      const id = '${PRODUCT_ID}';
      const html = document.body.innerHTML || '';
      const text = document.body.innerText || '';
      const count = (html.match(new RegExp(id, 'g')) || []).length;
      return { count, inVisibleText: text.includes(id) };
    }
    ```

    - `count >= 1` → product is in the showcase DOM. **Verified success.** Continue to Step 15.
    - `count == 0` → list may not have refreshed yet. Go to Step 14.

14. Reload and retry once:
    - `navigate_page` (type=reload).
    - `wait_for` text `["商品橱窗共有", "Showcase"]`, timeout 15000.
    - Re-run the same `evaluate_script` from Step 13.
    - `count >= 1` → verified success.
    - `count == 0` → emit this exact final line and stop the skill:

      `VERIFY_FAILED_PRODUCT_NOT_IN_SHOWCASE: ${PRODUCT_ID}`

      Do NOT quote this string in any earlier narrative — only emit it once at the end so the caller's regex matches deterministically.

15. Stop. Report: "Product ${PRODUCT_ID} added successfully (verified by id; count=N occurrences in showcase DOM, inVisibleText=true/false)."
