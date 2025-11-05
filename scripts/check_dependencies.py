"""
Скрипт проверки зависимостей для системы управления контекстом
Проверяет доступность Redis, Qdrant и наличие всех необходимых компонентов
"""
import os
import sys
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Вывод заголовка"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    """Вывод успешного сообщения"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    """Вывод сообщения об ошибке"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_warning(text: str):
    """Вывод предупреждения"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_info(text: str):
    """Вывод информационного сообщения"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def check_redis() -> Tuple[bool, str]:
    """Проверка доступности Redis"""
    try:
        import redis
        
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            socket_connect_timeout=3,
            socket_timeout=3
        )
        
        # Проверка подключения
        client.ping()
        
        # Проверка версии
        info = client.info()
        version = info.get('redis_version', 'unknown')
        
        return True, f"Redis доступен на {redis_host}:{redis_port} (версия {version})"
    except ImportError:
        return False, "Библиотека redis не установлена. Установите: pip install redis"
    except redis.ConnectionError as e:
        return False, f"Не удалось подключиться к Redis на {redis_host}:{redis_port}. Проверьте, что Redis запущен."
    except Exception as e:
        return False, f"Ошибка при проверке Redis: {str(e)}"


def check_qdrant() -> Tuple[bool, str]:
    """Проверка доступности Qdrant"""
    try:
        from qdrant_client import QdrantClient
        
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        
        if qdrant_api_key:
            client = QdrantClient(
                url=f"http://{qdrant_host}:{qdrant_port}",
                api_key=qdrant_api_key,
                timeout=3
            )
        else:
            client = QdrantClient(
                host=qdrant_host,
                port=qdrant_port,
                timeout=3
            )
        
        # Проверка подключения через получение коллекций
        collections = client.get_collections()
        
        return True, f"Qdrant доступен на {qdrant_host}:{qdrant_port} ({len(collections.collections)} коллекций)"
    except ImportError:
        return False, "Библиотека qdrant-client не установлена. Установите: pip install qdrant-client"
    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg or "timeout" in error_msg.lower():
            return False, f"Не удалось подключиться к Qdrant на {qdrant_host}:{qdrant_port}. Проверьте, что Qdrant запущен."
        return False, f"Ошибка при проверке Qdrant: {error_msg}"


def check_embedding_model() -> Tuple[bool, str]:
    """Проверка возможности загрузки модели эмбеддингов"""
    try:
        from sentence_transformers import SentenceTransformer
        import os
        
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        
        print_info(f"Загрузка модели {model_name}... (это может занять время при первом запуске)")
        
        model = SentenceTransformer(model_name)
        
        # Проверяем работу модели
        test_text = "Тестовый текст"
        embedding = model.encode(test_text)
        
        dimension = len(embedding)
        if dimension == 384:
            return True, f"Модель {model_name} загружена успешно (размерность: {dimension})"
        else:
            return False, f"Модель загружена, но размерность ({dimension}) не соответствует ожидаемой (384)"
    except ImportError:
        return False, "Библиотека sentence-transformers не установлена. Установите: pip install sentence-transformers"
    except Exception as e:
        error_msg = str(e)
        if "disk" in error_msg.lower() or "space" in error_msg.lower():
            return False, f"Недостаточно места на диске для загрузки модели: {error_msg}"
        return False, f"Ошибка при загрузке модели: {error_msg}"


def check_database() -> Tuple[bool, str]:
    """Проверка подключения к базе данных"""
    try:
        from database.database import engine
        
        with engine.connect() as conn:
            # Простая проверка подключения
            conn.execute("SELECT 1")
        
        database_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
        db_type = "PostgreSQL" if "postgresql" in database_url.lower() else "SQLite"
        
        return True, f"База данных доступна ({db_type})"
    except Exception as e:
        error_msg = str(e)
        if "OperationalError" in error_msg or "connection" in error_msg.lower():
            return False, f"Не удалось подключиться к базе данных. Проверьте DATABASE_URL в .env"
        return False, f"Ошибка при проверке базы данных: {error_msg}"


def check_rq_worker() -> Tuple[bool, str]:
    """Проверка возможности запуска RQ Worker"""
    try:
        import rq
        from rq import Queue
        from redis import Redis
        
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        
        # Проверяем, что можем создать очередь
        redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            socket_connect_timeout=3
        )
        redis_conn.ping()
        
        queue = Queue('context_tasks', connection=redis_conn)
        
        return True, f"RQ Worker готов к запуску (Redis доступен на {redis_host}:{redis_port})"
    except ImportError:
        return False, "Библиотека rq не установлена. Установите: pip install rq"
    except Exception as e:
        return False, f"Ошибка при проверке RQ: {str(e)}"


def check_environment_variables() -> List[Tuple[str, bool, str]]:
    """Проверка наличия необходимых переменных окружения"""
    results = []
    
    required_vars = {
        "DATABASE_URL": False,  # Опционально, есть дефолт
        "REDIS_HOST": False,
        "REDIS_PORT": False,
        "QDRANT_HOST": False,
        "QDRANT_PORT": False,
    }
    
    optional_vars = {
        "QDRANT_API_KEY": True,
        "REDIS_PASSWORD": True,
        "EMBEDDING_MODEL": True,
        "DEEPSEEK_API_KEY": True,
    }
    
    for var, is_optional in {**required_vars, **optional_vars}.items():
        value = os.getenv(var)
        if value:
            results.append((var, True, f"✅ {var} установлена"))
        elif is_optional:
            results.append((var, True, f"⚠️  {var} не установлена (опционально)"))
        else:
            results.append((var, False, f"❌ {var} не установлена"))
    
    return results


def main():
    """Основная функция проверки"""
    print_header("Проверка зависимостей системы управления контекстом")
    
    all_ok = True
    critical_errors = []
    warnings = []
    
    # Проверка переменных окружения
    print(f"\n{Colors.BOLD}Переменные окружения:{Colors.RESET}")
    env_results = check_environment_variables()
    for var, ok, msg in env_results:
        if ok:
            print(f"  {msg}")
        else:
            print(f"  {msg}")
            all_ok = False
            critical_errors.append(f"Не установлена переменная окружения: {var}")
    
    # Проверка базы данных
    print(f"\n{Colors.BOLD}База данных:{Colors.RESET}")
    db_ok, db_msg = check_database()
    if db_ok:
        print_success(db_msg)
    else:
        print_error(db_msg)
        all_ok = False
        critical_errors.append(db_msg)
    
    # Проверка Redis
    print(f"\n{Colors.BOLD}Redis (Очереди задач):{Colors.RESET}")
    redis_ok, redis_msg = check_redis()
    if redis_ok:
        print_success(redis_msg)
    else:
        print_error(redis_msg)
        all_ok = False
        critical_errors.append(redis_msg)
    
    # Проверка RQ Worker
    print(f"\n{Colors.BOLD}RQ Worker:{Colors.RESET}")
    rq_ok, rq_msg = check_rq_worker()
    if rq_ok:
        print_success(rq_msg)
    else:
        print_warning(rq_msg)
        warnings.append(rq_msg)
    
    # Проверка Qdrant
    print(f"\n{Colors.BOLD}Qdrant (Векторная БД):{Colors.RESET}")
    qdrant_ok, qdrant_msg = check_qdrant()
    if qdrant_ok:
        print_success(qdrant_msg)
    else:
        print_warning(qdrant_msg)
        warnings.append(f"Qdrant недоступен: {qdrant_msg}. Векторный поиск будет недоступен.")
    
    # Проверка модели эмбеддингов
    print(f"\n{Colors.BOLD}Модель эмбеддингов:{Colors.RESET}")
    model_ok, model_msg = check_embedding_model()
    if model_ok:
        print_success(model_msg)
    else:
        print_warning(model_msg)
        warnings.append(f"Модель эмбеддингов не загружена: {model_msg}. Векторизация будет недоступна.")
    
    # Итоговый результат
    print_header("Результат проверки")
    
    if all_ok:
        print_success("Все критические компоненты доступны!")
        if warnings:
            print(f"\n{Colors.YELLOW}Предупреждения:{Colors.RESET}")
            for warning in warnings:
                print(f"  • {warning}")
        print(f"\n{Colors.GREEN}Система готова к работе!{Colors.RESET}")
        print(f"\n{Colors.BLUE}Следующие шаги:{Colors.RESET}")
        print("  1. Запустите API сервер: uvicorn main:app --reload")
        print("  2. Запустите Context Worker: python run_context_worker.py")
        return 0
    else:
        print_error("Обнаружены критические ошибки!")
        print(f"\n{Colors.RED}Критические проблемы:{Colors.RESET}")
        for error in critical_errors:
            print(f"  • {error}")
        
        if warnings:
            print(f"\n{Colors.YELLOW}Предупреждения:{Colors.RESET}")
            for warning in warnings:
                print(f"  • {warning}")
        
        print(f"\n{Colors.YELLOW}Рекомендации:{Colors.RESET}")
        
        if not redis_ok:
            print("  • Запустите Redis: docker run -d -p 6379:6379 redis:latest")
            print("    Или установите локально: https://redis.io/download")
        
        if not qdrant_ok:
            print("  • Запустите Qdrant: docker run -d -p 6333:6333 qdrant/qdrant")
            print("    Или используйте облачный Qdrant: https://cloud.qdrant.io")
        
        if not model_ok:
            print("  • Установите sentence-transformers: pip install sentence-transformers")
            print("    Первая загрузка модели может занять время")
        
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Проверка прервана пользователем{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Неожиданная ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

