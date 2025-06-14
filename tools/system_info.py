#!/usr/bin/env python3
"""
System Information Tool - System metrics and status reporting

Provides system information like disk usage, memory, CPU, and process information.
Demonstrates external command execution and data formatting patterns.
"""
import os
import sys
import platform
import asyncio
import subprocess
from typing import Optional

sys.path.append('..')
from base_tool import BaseTool, ToolResult, ToolError


class SystemInfoTool(BaseTool):
    """
    System information and metrics reporting tool.
    
    Provides:
    - System overview (OS, Python version, etc.)
    - Disk usage information
    - Memory information  
    - CPU information
    - Current processes
    """
    
    name = "system_info"
    description = "Get system information, disk usage, memory, and process details"
    
    async def execute(self, info_type: str = "overview", path: Optional[str] = None) -> ToolResult:
        """
        Get system information.
        
        Args:
            info_type: Type of info ('overview', 'disk', 'memory', 'cpu', 'processes')
            path: Path for disk usage (optional, defaults to current directory)
        """
        try:
            if info_type == "overview":
                return await self._get_overview()
            elif info_type == "disk":
                return await self._get_disk_info(path or ".")
            elif info_type == "memory":
                return await self._get_memory_info()
            elif info_type == "cpu":
                return await self._get_cpu_info()
            elif info_type == "processes":
                return await self._get_process_info()
            else:
                raise ToolError(f"Unknown info_type: {info_type}. Use 'overview', 'disk', 'memory', 'cpu', or 'processes'")
                
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"System info failed: {str(e)}")
    
    async def _get_overview(self) -> ToolResult:
        """Get system overview"""
        result = ToolResult()
        
        result.add_text("🖥️  System Overview")
        result.add_text(f"📊 OS: {platform.system()} {platform.release()}")
        result.add_text(f"🏗️  Architecture: {platform.machine()}")
        result.add_text(f"🐍 Python: {platform.python_version()}")
        result.add_text(f"💻 Hostname: {platform.node()}")
        result.add_text(f"👤 User: {os.getenv('USER', 'unknown')}")
        result.add_text(f"📁 Working Dir: {os.getcwd()}")
        
        return result
    
    async def _get_disk_info(self, path: str) -> ToolResult:
        """Get disk usage information"""
        try:
            stat = await asyncio.to_thread(os.statvfs, path)
            
            # Calculate sizes in bytes
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bavail
            used = total - free
            
            # Convert to human readable
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            used_percent = (used / total) * 100 if total > 0 else 0
            
            result = ToolResult()
            result.add_text(f"💾 Disk Usage: {path}")
            result.add_text(f"📊 Total: {total_gb:.2f} GB")
            result.add_text(f"📈 Used: {used_gb:.2f} GB ({used_percent:.1f}%)")
            result.add_text(f"📉 Free: {free_gb:.2f} GB")
            
            # Add visual bar
            bar_length = 20
            used_bars = int((used_percent / 100) * bar_length)
            free_bars = bar_length - used_bars
            bar = "█" * used_bars + "░" * free_bars
            result.add_text(f"📊 [{bar}]")
            
            return result
            
        except FileNotFoundError:
            raise ToolError(f"Path not found: {path}")
        except Exception as e:
            raise ToolError(f"Failed to get disk info: {str(e)}")
    
    async def _get_memory_info(self) -> ToolResult:
        """Get memory information"""
        try:
            # Try to get memory info (Linux/macOS)
            if platform.system() == "Linux":
                meminfo = await self._read_proc_meminfo()
                return self._format_memory_linux(meminfo)
            elif platform.system() == "Darwin":  # macOS
                return await self._get_memory_macos()
            else:
                # Fallback for other systems
                return await self._get_memory_fallback()
                
        except Exception as e:
            raise ToolError(f"Failed to get memory info: {str(e)}")
    
    async def _read_proc_meminfo(self) -> dict:
        """Read /proc/meminfo on Linux"""
        meminfo = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        # Extract numeric value (remove 'kB' etc.)
                        numeric_value = ''.join(filter(str.isdigit, value))
                        if numeric_value:
                            meminfo[key] = int(numeric_value) * 1024  # Convert kB to bytes
            return meminfo
        except Exception:
            return {}
    
    def _format_memory_linux(self, meminfo: dict) -> ToolResult:
        """Format Linux memory info"""
        result = ToolResult()
        
        total = meminfo.get('MemTotal', 0)
        free = meminfo.get('MemFree', 0)
        available = meminfo.get('MemAvailable', free)
        used = total - available
        
        if total > 0:
            result.add_text("🧠 Memory Information")
            result.add_text(f"📊 Total: {total / (1024**3):.2f} GB")
            result.add_text(f"📈 Used: {used / (1024**3):.2f} GB")
            result.add_text(f"📉 Available: {available / (1024**3):.2f} GB")
            result.add_text(f"📊 Usage: {(used/total)*100:.1f}%")
        else:
            result.add_text("🧠 Memory info not available")
            
        return result
    
    async def _get_memory_macos(self) -> ToolResult:
        """Get memory info on macOS using vm_stat"""
        try:
            cmd = ["vm_stat"]
            proc = await asyncio.create_subprocess_exec(
                *cmd, 
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            result = ToolResult()
            result.add_text("🧠 Memory Information (macOS)")
            result.add_text(stdout.decode().strip())
            return result
            
        except Exception:
            return await self._get_memory_fallback()
    
    async def _get_memory_fallback(self) -> ToolResult:
        """Fallback memory info"""
        result = ToolResult()
        result.add_text("🧠 Memory Information")
        result.add_text("ℹ️  Detailed memory info not available on this platform")
        return result
    
    async def _get_cpu_info(self) -> ToolResult:
        """Get CPU information"""
        result = ToolResult()
        
        result.add_text("⚡ CPU Information")
        result.add_text(f"🏗️  Processor: {platform.processor()}")
        result.add_text(f"📊 Cores: {os.cpu_count()} cores")
        
        # Try to get load average (Unix systems)
        try:
            load = os.getloadavg()
            result.add_text(f"📈 Load Average: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}")
        except AttributeError:
            result.add_text("📈 Load Average: Not available on this platform")
        
        return result
    
    async def _get_process_info(self) -> ToolResult:
        """Get current process information"""
        result = ToolResult()
        
        result.add_text("🔄 Process Information")
        result.add_text(f"🆔 PID: {os.getpid()}")
        result.add_text(f"👨‍💼 Parent PID: {os.getppid()}")
        
        # Get process count (Unix systems)
        try:
            if platform.system() in ["Linux", "Darwin"]:
                cmd = ["ps", "aux"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    lines = stdout.decode().strip().split('\n')
                    process_count = len(lines) - 1  # Subtract header
                    result.add_text(f"📊 Total Processes: {process_count}")
                else:
                    result.add_text("📊 Process count: Unable to retrieve")
            else:
                result.add_text("📊 Process listing not available on this platform")
                
        except Exception as e:
            result.add_text(f"📊 Process info error: {str(e)}")
        
        return result


# Example usage and testing
if __name__ == "__main__":
    async def test_system_tool():
        tool = SystemInfoTool()
        
        print("🧪 Testing System Info Tool")
        print(f"Schema: {tool.input_schema}")
        
        # Test overview
        overview = await tool.execute("overview")
        print(f"Overview: {overview.to_dict()}")
        
        # Test disk
        disk = await tool.execute("disk", ".")
        print(f"Disk: {disk.to_dict()}")
    
    asyncio.run(test_system_tool())
