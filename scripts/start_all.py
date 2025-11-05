"""
Скрипт для запуска всех компонентов системы управления контекстом
Запускает API сервер и Context Worker в отдельных процессах
"""
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def check_dependencies():
    """Проверка зависимостей перед запуском"""
    print(f"{Colors.BOLD}Проверка зависимостей...{Colors.RESET}")
    
    result = subprocess.run(
        [sys.executable, "check_dependencies.py"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


def start_api_server():
    """Запуск API сервера"""
    print(f"\n{Colors.BOLD}Запуск API сервера...{Colors.RESET}")
    
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return process


def start_worker():
    """Запуск Context Worker"""
    print(f"\n{Colors.BOLD}Запуск Context Worker...{Colors.RESET}")
    
    cmd = [sys.executable, "run_context_worker.py"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return process


def main():
    """Основная функция"""
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}Запуск системы управления контекстом{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    # Проверка зависимостей
    if not check_dependencies():
        print_error("Не все зависимости доступны. Исправьте ошибки перед запуском.")
        print_info("Запустите: python check_dependencies.py")
        return 1
    
    processes = []
    
    try:
        # Запуск API сервера
        api_process = start_api_server()
        processes.append(("API Server", api_process))
        time.sleep(2)  # Даем время на запуск
        
        # Проверка, что API сервер запустился
        if api_process.poll() is not None:
            print_error("API сервер завершился с ошибкой")
            stdout, _ = api_process.communicate()
            print(stdout)
            return 1
        
        print_success("API сервер запущен на http://localhost:8000")
        print_info("Документация: http://localhost:8000/docs")
        
        # Запуск Worker
        worker_process = start_worker()
        processes.append(("Context Worker", worker_process))
        time.sleep(1)
        
        # Проверка, что Worker запустился
        if worker_process.poll() is not None:
            print_error("Context Worker завершился с ошибкой")
            stdout, _ = worker_process.communicate()
            print(stdout)
            return 1
        
        print_success("Context Worker запущен")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}Все компоненты запущены!{Colors.RESET}")
        print(f"{Colors.BLUE}Для остановки нажмите Ctrl+C{Colors.RESET}\n")
        
        # Ожидание завершения процессов
        while True:
            time.sleep(1)
            for name, proc in processes:
                if proc.poll() is not None:
                    print_error(f"{name} завершился неожиданно")
                    return 1
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Остановка всех процессов...{Colors.RESET}")
        
        for name, proc in processes:
            print_info(f"Остановка {name}...")
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print_success(f"{name} остановлен")
            except subprocess.TimeoutExpired:
                print_error(f"{name} не остановился, принудительное завершение...")
                proc.kill()
                proc.wait()
            except Exception as e:
                print_error(f"Ошибка при остановке {name}: {str(e)}")
        
        print_success("Все процессы остановлены")
        return 0
    
    except Exception as e:
        print_error(f"Ошибка при запуске: {str(e)}")
        
        # Остановка всех процессов
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                proc.kill()
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

