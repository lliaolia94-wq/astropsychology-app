"""
SQLite Queue Worker - бесплатная альтернатива RQ Worker
Обрабатывает задачи из SQLite очереди
"""
import os
import sys
import json
import importlib
import signal
import logging
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

load_dotenv()

from app.services.sqlite_queue_service import sqlite_queue_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Флаг для корректного завершения
shutdown_flag = False


def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения"""
    global shutdown_flag
    logger.info("\n🛑 Получен сигнал завершения, завершаем работу...")
    shutdown_flag = True


def load_function(func_name: str):
    """
    Загрузка функции по её полному имени (модуль.функция)
    
    Args:
        func_name: Полное имя функции, например "services.context_worker.process_context_save_task"
        
    Returns:
        Функция или None
    """
    try:
        module_path, function_name = func_name.rsplit('.', 1)
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        return func
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки функции {func_name}: {str(e)}")
        return None


def execute_task(task):
    """
    Выполнение задачи
    
    Args:
        task: Объект Task из SQLite очереди
    """
    job_id = task.job_id
    
    try:
        # Загружаем функцию
        func = load_function(task.function_name)
        if not func:
            sqlite_queue_service.mark_failed(job_id, f"Функция {task.function_name} не найдена")
            return
        
        # Десериализуем аргументы
        args = []
        if task.args_json:
            try:
                args = json.loads(task.args_json)
            except json.JSONDecodeError as e:
                sqlite_queue_service.mark_failed(job_id, f"Ошибка парсинга args: {str(e)}")
                return
        
        kwargs = {}
        if task.kwargs_json:
            try:
                kwargs = json.loads(task.kwargs_json)
            except json.JSONDecodeError as e:
                sqlite_queue_service.mark_failed(job_id, f"Ошибка парсинга kwargs: {str(e)}")
                return
        
        # Выполняем функцию
        logger.info(f"🚀 Выполнение задачи {job_id}: {task.function_name}")
        result = func(*args, **kwargs)
        
        # Отмечаем как выполненную
        sqlite_queue_service.mark_finished(job_id, result)
        logger.info(f"✅ Задача {job_id} выполнена успешно")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Ошибка выполнения задачи {job_id}: {error_msg}", exc_info=True)
        sqlite_queue_service.mark_failed(job_id, error_msg)


def main():
    """Запуск SQLite Queue Worker"""
    
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    queue_name = os.getenv("QUEUE_NAME", "context_tasks")
    
    print("=" * 60)
    print("🚀 SQLite Queue Worker")
    print("=" * 60)
    print(f"📋 Очередь: {queue_name}")
    print(f"💾 База данных: {sqlite_queue_service.db_url}")
    print("⏳ Ожидание задач...")
    print("(Для остановки нажмите Ctrl+C)")
    print("-" * 60)
    
    processed_count = 0
    
    try:
        while not shutdown_flag:
            # Получаем задачу из очереди (ждем до 5 секунд)
            task = sqlite_queue_service.dequeue(queue_name, timeout=5)
            
            if task:
                execute_task(task)
                processed_count += 1
            elif not shutdown_flag:
                # Если задачи нет, продолжаем ждать
                continue
            else:
                # Получен сигнал завершения
                break
        
        print(f"\n✅ Worker остановлен. Обработано задач: {processed_count}")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n\n👋 SQLite Worker остановлен. Обработано задач: {processed_count}")
        return 0
    except Exception as e:
        print(f"\n❌ Критическая ошибка в worker: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
