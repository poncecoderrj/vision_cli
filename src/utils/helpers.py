"""
Utils - Logger estruturado, retry com backoff, fuzzy match, helpers
"""

import logging
import time
import random
from typing import Callable, TypeVar, Optional, Any
from functools import wraps

T = TypeVar('T')


# Configuração de logger estruturado
def setup_logger(name: str = "agent", 
                 level: int = logging.INFO,
                 log_file: Optional[str] = None) -> logging.Logger:
    """
    Configura logger estruturado com formato padronizado
    
    Args:
        name: Nome do logger
        level: Nível de logging
        log_file: Caminho para arquivo de log (opcional)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Formato estruturado
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo (opcional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Logger global
logger = setup_logger()


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator para retry com backoff exponencial
    
    Args:
        max_attempts: Número máximo de tentativas
        base_delay: Delay inicial em segundos
        max_delay: Delay máximo em segundos
        exponential_base: Base para cálculo exponencial
        jitter: Adiciona aleatoriedade para evitar thundering herd
        exceptions: Tuple de exceptions que devem triggerar retry
    
    Returns:
        Decorator
    
    Exemplo:
        @retry_with_backoff(max_attempts=5, base_delay=0.5)
        def api_call():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Falha após {max_attempts} tentativas: {func.__name__}",
                            exc_info=True
                        )
                        break
                    
                    # Calcula delay com backoff exponencial
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    
                    # Adiciona jitter se solicitado
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"Tentativa {attempt}/{max_attempts} falhou para {func.__name__}: {e}. "
                        f"Retry em {delay:.2f}s"
                    )
                    
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


def fuzzy_match(query: str, text: str, threshold: float = 0.6) -> float:
    """
    Fuzzy match simples entre query e texto
    
    Args:
        query: String a buscar
        text: Texto onde buscar
        threshold: Threshold mínimo para considerar match
    
    Returns:
        Score de similaridade (0.0 a 1.0)
    """
    query = query.lower()
    text = text.lower()
    
    # Match exato retorna 1.0
    if query in text:
        return 1.0
    
    # Verifica se todos os caracteres da query aparecem em ordem
    query_idx = 0
    matches = 0
    
    for char in text:
        if query_idx < len(query) and char == query[query_idx]:
            matches += 1
            query_idx += 1
    
    if query_idx == len(query):
        # Todos os caracteres encontrados em ordem
        return matches / len(text)
    
    # Fallback: ratio de caracteres comuns
    common_chars = set(query) & set(text)
    return len(common_chars) / max(len(query), len(text))


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Trunca texto mantendo limite de caracteres"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_bytes(size: int) -> str:
    """Formata tamanho em bytes para humano legível"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_duration(seconds: float) -> str:
    """Formata duração em segundos para string legível"""
    if seconds < 1.0:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60.0:
        return f"{seconds:.1f}s"
    elif seconds < 3600.0:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


class Timer:
    """Context manager para timing de operações"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: float = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        logger.debug(f"{self.name} completed in {format_duration(self.elapsed)}")
