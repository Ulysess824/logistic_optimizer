import logging
from logging.handlers import TimedRotatingFileHandler
from rich.logging import RichHandler
import json
from datetime import datetime
from pathlib import Path

class JSONFormatter(logging.Formatter):
    """Formateador personalizado que convierte los logs de registro en JSON estructurado."""
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)

class LogManager:
    """Gestor centralizado de Logging para el proyecto GABM."""
    _configured = False

    @staticmethod
    def setup_logging(logs_dir: Path):
        """
        Configura el root logger con:
        - Un handler de consola usando Rich (Minimalista)
        - Un handler de archivo rotatorio usando JSON (Detallado)
        """
        if LogManager._configured:
            return
            
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "optimizer.log"
        
        # Asegurar que empezamos desde cero en el root logger
        root_logger = logging.getLogger()
        if root_logger.hasHandlers():
            root_logger.handlers.clear()
            
        root_logger.setLevel(logging.DEBUG) # Permitir DEBUG hacia abajo, los handlers filtran

        # 1. Consola (Minimalista) -> logging.INFO (Hitos principales)
        # Desactivamos el show_time y show_path para enfocarnos puramente en el mensaje del hito.
        console_handler = RichHandler(
            rich_tracebacks=True, 
            markup=True, 
            show_time=False, 
            show_path=False
        )
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        
        # 2. Archivo Físico (Auditoría Técnica) -> logging.DEBUG (Flujo completo) en JSON
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=30,  # Mantener logs por 30 días
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())

        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        # Para silenciar un poco a librerías de terceros ruidosas en consola
        logging.getLogger("googlemaps").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        LogManager._configured = True
