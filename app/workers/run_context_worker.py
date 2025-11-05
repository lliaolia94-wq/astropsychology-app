"""
Скрипт для запуска Context Worker (RQ Worker)
Обрабатывает задачи сохранения контекста из очереди Redis

Запуск:
    python run_context_worker.py

Или через RQ:
    rq worker context_tasks --url redis://localhost:6379
"""
import os
import sys
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

load_dotenv()

from rq import Worker, Queue, Connection
from redis import Redis

# Импортируем функции для обработки задач
from app.workers.context_worker import process_context_save_task

def check_dependencies():
    """Проверка зависимостей перед запуском"""
    errors = []
    
    # Проверка Redis
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            socket_connect_timeout=3
        )
        redis_conn.ping()
        print(f"✅ Redis подключен: {redis_host}:{redis_port}")
    except Exception as e:
        errors.append(f"❌ Redis недоступен: {str(e)}")
        errors.append("   Запустите Redis: docker run -d -p 6379:6379 redis:latest")
    
    # Проверка Qdrant (опционально)
    try:
        from qdrant_client import QdrantClient
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        
        client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=3)
        client.get_collections()
        print(f"✅ Qdrant подключен: {qdrant_host}:{qdrant_port}")
    except Exception as e:
        print(f"⚠️  Qdrant недоступен: {str(e)}")
        print("   Векторизация будет недоступна. Для запуска: docker run -d -p 6333:6333 qdrant/qdrant")
    
    if errors:
        print("\n❌ Критические ошибки:")
        for error in errors:
            print(f"   {error}")
        return False
    
    return True


def main():
    """Запуск RQ Worker для обработки задач контекста"""
    
    print("=" * 60)
    print("Context Worker - Запуск проверки зависимостей")
    print("=" * 60)
    
    # Проверяем зависимости
    redis_available = check_dependencies()
    
    if not redis_available:
        print("\n⚠️  ВНИМАНИЕ: Redis недоступен!")
        print("   Переключаемся на SQLite-основанную очередь (бесплатная альтернатива).")
        print("\n   Для использования Redis (опционально):")
        print("   1. Docker: docker run -d -p 6379:6379 redis:latest")
        print("   2. WSL2: sudo apt-get install redis-server")
        print("   3. Memurai (Windows): https://www.memurai.com/get-memurai")
        print("\n✅ Используем SQLite Queue Worker...")
        print("-" * 60)
        # Запускаем SQLite worker
        import run_sqlite_worker
        return run_sqlite_worker.main()
    
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))
    redis_password = os.getenv("REDIS_PASSWORD", None)
    
    # Подключение к Redis
    try:
        redis_conn = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            socket_connect_timeout=5
        )
        redis_conn.ping()
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {str(e)}")
        return 1
    
    # Создаем очередь
    queue = Queue('context_tasks', connection=redis_conn)
    
    print("\n" + "=" * 60)
    print("🚀 Запуск Context Worker")
    print("=" * 60)
    print(f"📡 Подключение к Redis: {redis_host}:{redis_port}")
    print(f"📋 Очередь: context_tasks")
    print("⏳ Ожидание задач...")
    print("(Для остановки нажмите Ctrl+C)")
    print("-" * 60)
    
    # Создаем воркер
    try:
        with Connection(redis_conn):
            worker = Worker([queue], name='context_worker')
            worker.work()
    except KeyboardInterrupt:
        print("\n\n👋 Context Worker остановлен")
        return 0
    except Exception as e:
        print(f"\n❌ Ошибка в worker: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

