<!-- QUESTIONS
[
  {"id": "url",     "ask": "URL do site que quer raspar?",          "type": "text", "default": "https://",                                                                   "label": "URL alvo"},
  {"id": "target",  "ask": "O que quer extrair?",                   "options": ["Textos/artigos", "Preços/produtos", "Links/URLs", "Tabelas de dados", "Imagens"],           "label": "Dado a extrair"},
  {"id": "output",  "ask": "Formato de saída?",                     "options": ["JSON", "CSV", "Texto simples"],                                                             "label": "Formato de saída"},
  {"id": "pages",   "ask": "Precisa paginar (múltiplas páginas)?",  "options": ["Não, só uma página", "Sim, múltiplas páginas"],                                             "label": "Paginação"},
  {"id": "name",    "ask": "Nome do arquivo de saída?",             "type": "text", "default": "output",                                                                     "label": "Nome do arquivo"}
]
-->

# SKILL: Web Scraper / Coletor de Dados

As configurações já foram coletadas. Execute os passos abaixo em ordem.

## PASSOS

### 1. Inspecionar a página alvo
```
fetch_url("{url}")
```
Analise o conteúdo retornado: identifique padrões de texto, estrutura HTML, onde ficam os dados.

### 2. Verificar robots.txt
```
fetch_url("{url}/robots.txt")
```
Confirme que o scraping é permitido antes de prosseguir.

### 3. Criar o scraper

**Para páginas estáticas (HTML simples):**
```python
# scraper.py
import requests
from bs4 import BeautifulSoup
import json, csv, time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def scrape_page(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    # adaptar o seletor ao conteúdo real visto no fetch_url
    items = soup.find_all("seletor_adequado")
    return [{"texto": el.get_text(strip=True)} for el in items]
```

**Para páginas com JavaScript (dinâmicas):**
```python
from playwright.sync_api import sync_playwright

def scrape_dynamic(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")
        # extrair dados
        browser.close()
```

### 4. Adicionar paginação (se Sim)
```python
results = []
page = 1
while True:
    data = scrape_page(f"{url}?page={page}")
    if not data:
        break
    results.extend(data)
    page += 1
    time.sleep(1)  # respeita o servidor
```

### 5. Salvar no formato escolhido
- JSON: `json.dump(results, open("{name}.json","w"), ensure_ascii=False, indent=2)`
- CSV: `csv.DictWriter(open("{name}.csv","w"), fieldnames=results[0].keys())`
- Texto: `open("{name}.txt","w").write("\n".join(str(r) for r in results))`

### 6. Instalar dependências e rodar
```
pip install requests beautifulsoup4
python scraper.py
```
Mostre quantos itens foram coletados e onde foram salvos.
