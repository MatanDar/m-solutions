name: Update CSV with Hot Products

on:
  workflow_dispatch:  # Manual trigger
  schedule:
    - cron: '0 */12 * * *'  # Run every 12 hours (optional)

permissions:
  contents: write  # This allows the workflow to push changes

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run update script
        run: |
          python scripts/update_csv.py

      - name: Check for changes
        id: check_changes
        run: |
          if git diff --quiet products.csv; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
          fi

      - name: Commit and push changes
        if: steps.check_changes.outputs.changed == 'true'
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add products.csv
          git commit -m "🔥 Auto-update: Added hot products from AliExpress [$(date +'%Y-%m-%d %H:%M')]"
          git push