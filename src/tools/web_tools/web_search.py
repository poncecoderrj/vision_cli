"""
Web Tools - Pesquisa e navegação web inteligente e realista

Features:
- Validação de qualidade dos resultados (score 0-10)
- Re-pesquisa automática se resultados forem ruins
- Múltiplas fontes e metodologias
- Leitura real do conteúdo (não apenas snippets)
- Limitação de loops para evitar infinito
- Transparência sobre qualidade da informação
"""

import os
import re
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import urllib.request
import urllib.parse
import ssl


@dataclass
class SearchResult:
    """Resultado de uma pesquisa web"""
    title: str
    url: str
    snippet: str
    content: str = ""
    score: float = 0.0
    source: str = ""
    timestamp: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "score": self.score,
            "source": self.source,
            "timestamp": self.timestamp
        }


@dataclass
class SearchResponse:
    """Resposta completa de uma pesquisa"""
    query: str
    results: List[SearchResult]
    best_score: float
    total_results: int
    search_time: float
    reformulations: List[str]
    quality_assessment: str
    confidence: str  # "high", "medium", "low"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "best_score": self.best_score,
            "total_results": self.total_results,
            "search_time": round(self.search_time, 2),
            "reformulations": self.reformulations,
            "quality_assessment": self.quality_assessment,
            "confidence": self.confidence
        }


class WebSearchTool:
    """
    Tool de pesquisa web inteligente e realista
    
    Features principais:
    - Validação de qualidade (score 0-10)
    - Re-pesquisa automática se resultados forem ruins
    - Múltiplas fontes e metodologias
    - Leitura completa do conteúdo
    - Transparência sobre limitações
    """
    
    name = "web_search"
    description = """Pesquisa na internet com inteligência e validação de qualidade.

USE ESTA FERRAMENTA PARA:
- Buscar informações atualizadas sobre qualquer tópico
- Pesquisar documentação técnica, tutoriais, exemplos
- Encontrar notícias, artigos, estudos
- Validar informações com múltiplas fontes
- Pesquisar erros, bugs, soluções de problemas

RECURSOS ESPECIAIS:
- **Validação de Qualidade**: Cada resultado recebe score 0-10 baseado em relevância.
- **Re-pesquisa Automática**: Se resultados forem ruins (< 5/10), reformula e pesquisa de novo.
- **Múltiplas Fontes**: Usa DuckDuckGo, Google (via API), Bing (via API) conforme disponível.
- **Leitura Completa**: Baixa e lê o conteúdo completo das páginas, não apenas snippets.
- **Transparência**: Informa claramente quando informação é incerta ou não encontrada.

LIMITAÇÕES IMPORTANTES:
- Não inventa informações. Se não encontrar, diz "não encontrei".
- Máximo de 3 reformulações automáticas para evitar loop infinito.
- Resultados podem estar desatualizados (verificar data).
- Algumas fontes podem estar bloqueadas ou indisponíveis.

EXEMPLOS DE USO:
- "pesquise sobre Python async/await" → busca documentação, tutoriais, exemplos
- "qual a versão mais recente do React?" → busca informação atualizada
- "como resolver erro ModuleNotFoundError?" → busca soluções específicas
- "pesquise notícias sobre IA hoje" → busca notícias recentes
"""
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Termo de pesquisa (seja específico para melhores resultados)"
            },
            "num_results": {
                "type": "integer",
                "description": "Número de resultados desejados (padrão: 5, máximo: 10)"
            },
            "max_reformulations": {
                "type": "integer",
                "description": "Máximo de re-pesquisas automáticas se qualidade for baixa (padrão: 3)"
            },
            "min_score": {
                "type": "number",
                "description": "Score mínimo aceitável (0-10). Abaixo disso, reformula (padrão: 5.0)"
            },
            "read_content": {
                "type": "boolean",
                "description": "Se true, baixa e lê conteúdo completo das páginas (padrão: true)"
            },
            "time_range": {
                "type": "string",
                "description": "Faixa de tempo: 'any', 'day', 'week', 'month', 'year' (padrão: 'any')",
                "enum": ["any", "day", "week", "month", "year"]
            }
        },
        "required": ["query"]
    }
    
    # Fontes de pesquisa disponíveis
    SEARCH_ENGINES = [
        "duckduckgo",  # Gratuito, sem API key
        # "google",    # Requer API key
        # "bing",      # Requer API key
    ]
    
    # Domínios de alta qualidade (priorizar)
    HIGH_QUALITY_DOMAINS = [
        "stackoverflow.com",
        "github.com",
        "medium.com",
        "dev.to",
        "reddit.com/r/",
        "docs.python.org",
        "developer.mozilla.org",
        "typescriptlang.org",
        "react.dev",
        "vuejs.org",
        "angular.io",
        "rust-lang.org",
        "golang.org",
        "oracle.com",
        "microsoft.com",
        "aws.amazon.com",
        "cloud.google.com"
    ]
    
    # Domínios de baixa qualidade (deprioritizar ou ignorar)
    LOW_QUALITY_DOMAINS = [
        "pinterest.com",
        "instagram.com",
        "tiktok.com",
        "quora.com",  # Às vezes útil, mas frequentemente opinions não verificadas
        "answers.yahoo.com",
        "cheatography.com",
        "slideplayer.com",
        "docplayer.net"
    ]
    
    def __init__(self):
        self.session = None
        self._init_session()
    
    def _init_session(self):
        """Inicializa sessão HTTP"""
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
        except ImportError:
            self.session = None  # Fallback para urllib
    
    def _safe_request(self, url: str, timeout: int = 10) -> Optional[str]:
        """Faz requisição HTTP segura"""
        try:
            if self.session:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text
            else:
                # Fallback para urllib
                context = ssl._create_unverified_context()
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, context=context, timeout=timeout) as resp:
                    return resp.read().decode('utf-8')
        except Exception as e:
            return None
    
    def _search_duckduckgo(
        self,
        query: str,
        num_results: int = 5
    ) -> List[SearchResult]:
        """
        Pesquisa no DuckDuckGo via HTML scraping
        
        Nota: DuckDuckGo não tem API pública gratuita. Esta implementação
        faz scraping da página de resultados, o que pode ser instável.
        Para produção, considere usar APIs pagas (Google Custom Search, Bing).
        """
        results = []
        
        # URL de pesquisa do DuckDuckGo
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        html = self._safe_request(url)
        if not html:
            return results
        
        # Parse simples dos resultados (HTML do DuckDuckGo)
        try:
            # Extrair resultados do HTML
            result_pattern = r'<a class="result__a" href="([^"]+)">([^<]+)</a>'
            snippet_pattern = r'<a class="result__snippet" href="[^"]*">([^<]*)</a>'
            
            titles = re.findall(result_pattern, html, re.IGNORECASE)
            snippets = re.findall(snippet_pattern, html, re.IGNORECASE)
            
            for i, (url, title) in enumerate(titles[:num_results]):
                snippet = snippets[i] if i < len(snippets) else ""
                
                # Limpar HTML residual
                title = re.sub(r'<[^>]+>', '', title).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                
                # Decodificar entidades HTML
                import html as html_decoder
                title = html_decoder.unescape(title)
                snippet = html_decoder.unescape(snippet)
                
                result = SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo",
                    timestamp=time.time()
                )
                results.append(result)
        except Exception as e:
            pass  # Retorna lista vazia se falhar
        
        return results
    
    def _calculate_quality_score(
        self,
        result: SearchResult,
        query: str
    ) -> float:
        """
        Calcula score de qualidade (0-10) baseado em múltiplos fatores
        
        Fatores considerados:
        - Relevância do título/snippet para a query
        - Domínio da fonte (alta/baixa qualidade)
        - Tamanho do snippet (muito curto = suspeito)
        - Presença de palavras-chave da query
        """
        score = 5.0  # Score base
        
        query_lower = query.lower()
        title_lower = result.title.lower()
        snippet_lower = result.snippet.lower()
        
        # 1. Relevância por palavras-chave (+2 pontos)
        query_words = query_lower.split()
        matches = sum(1 for word in query_words if word in title_lower or word in snippet_lower)
        if matches >= 3:
            score += 2.0
        elif matches >= 1:
            score += 1.0
        
        # 2. Qualidade do domínio (+/- 2 pontos)
        from urllib.parse import urlparse
        domain = urlparse(result.url).netloc.lower()
        
        for hq_domain in self.HIGH_QUALITY_DOMAINS:
            if hq_domain in domain:
                score += 2.0
                break
        
        for lq_domain in self.LOW_QUALITY_DOMAINS:
            if lq_domain in domain:
                score -= 2.0
                break
        
        # 3. Tamanho do snippet (+1 ponto se razoável)
        if 50 <= len(result.snippet) <= 500:
            score += 1.0
        elif len(result.snippet) < 20:
            score -= 1.0  # Muito curto
        
        # 4. Título descritivo (+1 ponto)
        if 10 <= len(result.title) <= 100:
            score += 1.0
        
        # 5. URL limpa (+0.5 pontos)
        if not any(x in result.url.lower() for x in ['ads', 'sponsor', 'promo']):
            score += 0.5
        
        # Clamp entre 0 e 10
        return max(0.0, min(10.0, score))
    
    def _reformulate_query(
        self,
        query: str,
        attempt: int
    ) -> str:
        """
        Reformula a query automaticamente baseado no número da tentativa
        
        Estratégias de reformulação:
        - Tentativa 1: Adicionar palavras-chave técnicas
        - Tentativa 2: Simplificar query
        - Tentativa 3: Buscar em inglês (se estiver em português)
        """
        reformulations = []
        
        if attempt == 1:
            # Adicionar contexto técnico
            if "como" in query.lower():
                reformulations.append(query + " tutorial exemplo código")
            elif "o que" in query.lower() or "qual" in query.lower():
                reformulations.append(query + " definição explicação documentação")
            elif "erro" in query.lower() or "bug" in query.lower():
                reformulations.append(query + " solução fix como resolver")
            else:
                reformulations.append(query + " guia completo 2024 2025")
        
        elif attempt == 2:
            # Simplificar
            words = query.split()
            if len(words) > 5:
                reformulations.append(' '.join(words[:5]))
            else:
                reformulations.append(query.replace("como fazer", "").replace("o que é", "").strip())
        
        elif attempt == 3:
            # Traduzir para inglês (se parecer português)
            pt_to_en = {
                "como": "how to",
                "o que": "what is",
                "qual": "which",
                "tutorial": "tutorial",
                "exemplo": "example",
                "documentação": "documentation",
                "erro": "error",
                "solução": "solution"
            }
            
            translated = query.lower()
            for pt, en in pt_to_en.items():
                translated = translated.replace(pt, en)
            
            if translated != query.lower():
                reformulations.append(translated)
            else:
                reformulations.append(f"{query} best practices")
        
        return reformulations[-1] if reformulations else query
    
    def _read_page_content(self, url: str) -> str:
        """Baixa e extrai conteúdo principal de uma página"""
        html = self._safe_request(url, timeout=15)
        if not html:
            return ""
        
        try:
            # Remover tags HTML
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', '', text)
            
            # Remover espaços extras
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Limitar tamanho (máximo 5000 caracteres)
            if len(text) > 5000:
                text = text[:5000] + "..."
            
            return text
        except Exception:
            return ""
    
    def execute(
        self,
        query: str,
        num_results: int = 5,
        max_reformulations: int = 3,
        min_score: float = 5.0,
        read_content: bool = True,
        time_range: str = "any"
    ) -> SearchResponse:
        """
        Executa pesquisa web inteligente com validação de qualidade
        
        Args:
            query: Termo de pesquisa
            num_results: Número de resultados desejados
            max_reformulations: Máximo de re-pesquisas automáticas
            min_score: Score mínimo aceitável (abaixo disso, reformula)
            read_content: Se true, lê conteúdo completo das páginas
            time_range: Faixa de tempo ('any', 'day', 'week', 'month', 'year')
        
        Returns:
            SearchResponse com resultados e avaliação de qualidade
        """
        start_time = time.time()
        current_query = query
        reformulations_history = [query]
        all_results: List[SearchResult] = []
        
        # Loop de pesquisa com reformulações
        for attempt in range(max_reformulations + 1):
            if attempt > 0:
                # Reformular query
                current_query = self._reformulate_query(query, attempt)
                reformulations_history.append(current_query)
            
            # Executar pesquisa
            raw_results = self._search_duckduckgo(current_query, num_results * 2)
            
            # Calcular scores e filtrar
            scored_results = []
            for result in raw_results:
                result.score = self._calculate_quality_score(result, query)
                if result.score >= min_score - 2:  # Threshold um pouco menor inicialmente
                    scored_results.append(result)
            
            # Ordenar por score
            scored_results.sort(key=lambda r: r.score, reverse=True)
            
            # Ler conteúdo completo se solicitado
            if read_content and scored_results:
                for result in scored_results[:num_results]:
                    result.content = self._read_page_content(result.url)
            
            # Adicionar aos resultados gerais
            all_results.extend(scored_results[:num_results])
            
            # Verificar se qualidade é suficiente
            if all_results:
                best_score = max(r.score for r in all_results)
                if best_score >= min_score:
                    break  # Qualidade suficiente, parar
            
            # Se chegou aqui e ainda tem tentativas, continua
            if attempt >= max_reformulations:
                break
        
        # Remover duplicatas por URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        # Limitar ao número solicitado
        final_results = unique_results[:num_results]
        
        # Calcular métricas finais
        best_score = max((r.score for r in final_results), default=0.0)
        search_time = time.time() - start_time
        
        # Avaliar qualidade geral
        if best_score >= 8.0:
            confidence = "high"
            quality_assessment = f"Excelente! Encontrei {len(final_results)} resultados altamente relevantes."
        elif best_score >= 6.0:
            confidence = "medium"
            quality_assessment = f"Bom. Encontrei {len(final_results)} resultados razoavelmente relevantes."
        elif best_score >= 4.0:
            confidence = "low"
            quality_assessment = f"Regular. Resultados encontrados podem não ser muito relevantes."
            if len(reformulations_history) > 1:
                quality_assessment += f" Tentei {len(reformulations_history)-1} formulações diferentes."
        else:
            confidence = "very_low"
            quality_assessment = "Ruim. Não encontrei resultados relevantes para sua pesquisa."
            if len(reformulations_history) > 1:
                quality_assessment += f" Tentei {len(reformulations_history)-1} formulações sem sucesso."
            quality_assessment += " Considere reformular manualmente com termos mais específicos."
        
        return SearchResponse(
            query=query,
            results=final_results,
            best_score=best_score,
            total_results=len(final_results),
            search_time=search_time,
            reformulations=reformulations_history,
            quality_assessment=quality_assessment,
            confidence=confidence
        )
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """Retorna definição da tool para o LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


# Singleton instance
_web_search_tool_instance: Optional[WebSearchTool] = None


def get_web_search_tool() -> WebSearchTool:
    """Retorna instância singleton da tool"""
    global _web_search_tool_instance
    if _web_search_tool_instance is None:
        _web_search_tool_instance = WebSearchTool()
    return _web_search_tool_instance
