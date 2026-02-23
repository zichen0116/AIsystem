"""
开发环境一键启动脚本
同时启动：Redis、PostgreSQL、FastAPI、Celery Worker
"""
import subprocess
import sys
import os
import time
import signal

# 颜色输出
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'


def print_status(status, message):
    colors = {
        "INFO": GREEN,
        "WARN": YELLOW,
        "ERROR": RED
    }
    print(f"{colors.get(status, '')}[{status}]{RESET} {message}")


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
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'text': True,
            'bufsize': 1
        }
        
        if sys.platform == 'win32':
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        
        proc = subprocess.Popen(command, **kwargs)
        self.processes.append((name, proc))
        
        if need_wait:
            time.sleep(3)  # 等待服务启动
        
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
            time.sleep(2)
        else:
            print_status("INFO", "Redis 已运行")
        
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
            time.sleep(3)
        else:
            print_status("INFO", "PostgreSQL 已运行")
        
        # 3. 启动 FastAPI
        manager.start_process(
            "FastAPI",
            [sys.executable, "run.py"],
            cwd=backend_dir,
            need_wait=True
        )
        
        # 4. 启动 Celery Worker
        manager.start_process(
            "Celery Worker",
            [sys.executable, "-m", "celery", "-A", "app.celery", 
             "worker", "--loglevel=info"],
            cwd=backend_dir,
            need_wait=True
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