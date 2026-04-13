"""
开发环境一键启动脚本
同时启动：Redis、PostgreSQL、FastAPI、Celery Worker
"""
import subprocess
import sys
import os
import socket
import time
import signal
import urllib.error
import urllib.request

# 颜色输出
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'


def build_celery_worker_command(python_executable, platform=None):
    current_platform = platform or sys.platform
    command = [
        python_executable, "-m", "celery", "-A", "app.celery",
        "worker", "--loglevel=info", "-Q", "default,celery",
    ]
    if current_platform == 'win32':
        command.extend(["--pool=solo", "--concurrency=1"])
    return command


def print_status(status, message):
    colors = {
        "INFO": GREEN,
        "WARN": YELLOW,
        "ERROR": RED
    }
    print(f"{colors.get(status, '')}[{status}]{RESET} {message}")


def build_child_process_env(env=None):
    child_env = dict(env or os.environ)
    child_env.setdefault("PYTHONUNBUFFERED", "1")
    return child_env


def is_port_open(host, port, timeout=1.0):
    """检查 TCP 端口是否可连接"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_http_ready(url, timeout=2.0):
    """检查 HTTP 健康接口是否可用"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_for_condition(name, checker, retries=30, interval=1, process=None):
    """轮询直到条件满足，避免固定等待导致的启动竞态"""
    last_error = None
    for attempt in range(1, retries + 1):
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"{name} exited before ready")
        try:
            if checker():
                print_status("INFO", f"{name} 已就绪")
                return True
        except Exception as exc:  # pragma: no cover - 防御性分支
            last_error = exc
        if attempt < retries:
            time.sleep(interval)

    message = f"{name} 未在 {retries * interval} 秒内就绪"
    if last_error is not None:
        message = f"{message}: {last_error}"
    raise TimeoutError(message)


class ProcessManager:
    """进程管理器"""
    
    def __init__(self):
        self.processes = []
    
    def start_process(self, name, command, cwd=None, need_wait=False):
        """启动一个进程"""
        print_status("INFO", f"启动 {name}...")
        print_status("INFO", f"  命令: {' '.join(command)}")
        
        # Windows 下 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        # 用于正确处理 Ctrl+C
        kwargs = {
            'cwd': cwd,
            'env': build_child_process_env(),
        }
        
        if sys.platform == 'win32':
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        
        proc = subprocess.Popen(command, **kwargs)
        self.processes.append((name, proc))
        return proc
    
    def stop_all(self):
        """停止所有进程"""
        print_status("WARN", "正在停止所有服务...")
        
        for name, proc in self.processes:
            try:
                if sys.platform == 'win32':
                    proc.terminate()
                else:
                    proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                print_status("ERROR", f"停止 {name} 失败: {e}")
        
        self.processes.clear()
        print_status("INFO", "所有服务已停止")


def main():
    print("=" * 60)
    print("  多模态 AI 互动式教学智能体 - 开发环境启动")
    print("=" * 60)
    
    manager = ProcessManager()
    
    # 确保在 backend 目录
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查 Docker 是否运行
    try:
        subprocess.run(['docker', '--version'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_status("ERROR", "Docker 未安装或未运行，请先启动 Docker Desktop")
        sys.exit(1)
    
    try:
        # 1. 启动 Redis（如果还没启动）
        print_status("INFO", "检查 Redis...")
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=redis', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        if 'redis' not in result.stdout:
            print_status("INFO", "启动 Redis...")
            subprocess.Popen(
                ['docker', 'run', '-d', '--name', 'redis', 
                 '-p', '6379:6379', 'redis:7-alpine'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            print_status("INFO", "Redis 已运行")
        wait_for_condition("Redis", lambda: is_port_open("127.0.0.1", 6379))
        
        # 2. 启动 PostgreSQL（如果还没启动）
        print_status("INFO", "检查 PostgreSQL...")
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=postgres', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        if 'postgres' not in result.stdout:
            print_status("INFO", "启动 PostgreSQL...")
            subprocess.Popen(
                ['docker', 'run', '-d', '--name', 'postgres-dev',
                 '-e', 'POSTGRES_USER=postgres',
                 '-e', 'POSTGRES_PASSWORD=123456',
                 '-e', 'POSTGRES_DB=ai_teaching',
                 '-p', '5432:5432',
                 'postgres:15-alpine'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            print_status("INFO", "PostgreSQL 已运行")
        wait_for_condition("PostgreSQL", lambda: is_port_open("127.0.0.1", 5432), retries=60)

        # 3. 启动 FastAPI
        fastapi_proc = manager.start_process(
            "FastAPI",
            [sys.executable, "run.py"],
            cwd=backend_dir,
            need_wait=False
        )
        wait_for_condition(
            "FastAPI",
            lambda: is_http_ready("http://127.0.0.1:8000/health"),
            retries=60,
            process=fastapi_proc,
        )
        
        # 4. 启动 Celery Worker
        worker_command = build_celery_worker_command(sys.executable)

        manager.start_process(
            "Celery Worker",
            worker_command,
            cwd=backend_dir,
            need_wait=False
        )
        
        # 打印启动信息
        print("\n" + "=" * 60)
        print_status("INFO", "所有服务启动成功！")
        print("=" * 60)
        print(f"{GREEN}FastAPI:    http://localhost:8000{RESET}")
        print(f"{GREEN}API 文档:   http://localhost:8000/docs{RESET}")
        print(f"{GREEN}Redis:      localhost:6379{RESET}")
        print(f"{GREEN}PostgreSQL: localhost:5432{RESET}")
        print("=" * 60)
        print("\n按 Ctrl+C 停止所有服务...\n")
        
        # 等待并监控进程
        while True:
            time.sleep(1)
            
            # 检查 FastAPI 是否还在运行
            _, fastapi_proc = manager.processes[0]
            if fastapi_proc.poll() is not None:
                print_status("ERROR", "FastAPI 已停止，退出")
                break
            
            # 检查 Celery Worker 是否还在运行
            _, worker_proc = manager.processes[1]
            if worker_proc.poll() is not None:
                print_status("ERROR", "Celery Worker 已停止，退出")
                break
    
    except KeyboardInterrupt:
        print("\n")
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()
