name: Normalitzador de Productes

on:
  workflow_dispatch:

jobs:
  normalitzar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install requests gspread oauth2client
      - name: Run normalitzador
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
        run: python normalitzador.py
