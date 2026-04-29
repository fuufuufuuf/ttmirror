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
10. `take_snapshot`. Find the dialog's submit `button "添加商品"` (alongside `C`, NOT the page-level button). Its `disabled` state IS the affiliate-eligibility signal:
    - **Still `disableable disabled`** → product is NOT in the affiliate program. `click C` to close the dialog, then **stop the entire skill** and emit this exact final line:

      `NON_AFFILIATE_PRODUCT: 此商品不是联盟营销商品。请联系卖家，以将其注册到联盟计划中`

      Do NOT text-match the Chinese error in the snapshot — the toast may not render in the a11y tree, and quoting the string in your own narrative would false-trigger the caller's regex.
    - **Enabled (no `disabled`)** → continue. Capture this submit button's uid as **`S`**.

### Part 4: Submit and close

11. `click S` with `includeSnapshot=true`. From the returned snapshot, verify ONE of these terminal states:
    - The product card now shows an `"已添加"` badge (already-in-showcase de-dupe; treat as success), OR
    - The showcase counter `"商品橱窗共有 N 件商品"` increased vs. `before_count` from Step 4.

    Neither → report the snapshot's relevant text verbatim (likely an error toast).
12. The dialog does NOT auto-close. `click C` (or the top-right `×`) to close it. `take_snapshot` and confirm `tabpanel "商品链接"` is gone.
13. Stop. Report: "Product ${PRODUCT_ID} submit completed (state: <已添加 / counter +1 / verbatim>)."
