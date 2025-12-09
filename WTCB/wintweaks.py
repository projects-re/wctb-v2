import winreg
import ctypes
from ctypes import wintypes
from typing import List, Tuple, Dict, Any, TypedDict
import os
import psutil
import shutil
import tempfile
import logging
import subprocess
 
class StartupProgram(TypedDict):
    name: str
    path: str
    scope: str
    enabled: bool


class WinTweaks:
    """Handles applying tweaks to the Windows Registry."""

    @staticmethod
    def _broadcast_setting_change():
        """Notifies the system that a setting has changed to force a refresh."""
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_long()
        # Using a generic "Environment" string is often effective for Explorer settings.
        ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))


    @staticmethod
    def set_file_extensions(show: bool):
        """Set the HideFileExt value in the registry."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "HideFileExt", 0, winreg.REG_DWORD, 0 if show else 1)
            winreg.CloseKey(key)
            WinTweaks._broadcast_setting_change()
            return True, None
        except Exception as e:
            return False, f"Error setting file extension visibility: {e}"

    @staticmethod
    def set_hidden_files(show: bool):
        """Set the Hidden value in the registry to show or hide hidden files."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_SET_VALUE)
            # 1 = Show, 2 = Don't Show
            winreg.SetValueEx(key, "Hidden", 0, winreg.REG_DWORD, 1 if show else 2) 
            winreg.CloseKey(key)
            WinTweaks._broadcast_setting_change()
            return True, None
        except Exception as e:
            return False, f"Error setting hidden files visibility: {e}"

    @staticmethod
    def set_windows_theme(dark: bool):
        """Set the Windows theme to light or dark."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_SET_VALUE)
            # This key controls the theme for the OS itself (taskbar, start menu)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 0 if dark else 1)
            winreg.CloseKey(key)
            WinTweaks._broadcast_setting_change()
            return True, None
        except Exception as e:
            return False, f"Error setting Windows theme: {e}"

    @staticmethod
    def set_apps_theme(dark: bool):
        """Set the Apps theme to light or dark."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_SET_VALUE)
            # This key controls the theme for applications (File Explorer, Settings, etc.)
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0 if dark else 1)
            winreg.CloseKey(key)
            WinTweaks._broadcast_setting_change()
            return True, None
        except Exception as e:
            return False, f"Error setting Apps theme: {e}"

    @staticmethod
    def set_full_path_in_title(show: bool):
        """Show the full path in the File Explorer title bar."""
        try:
            # This is a bit tricky as it's in a binary blob.
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\CabinetState", 0, winreg.KEY_SET_VALUE)
            # The value is a binary structure, setting it directly is safer than trying to modify parts of it.
            # A known value for showing full path is b'\x0b\x00\x00\x00\x16\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00'
            # A known value for hiding it is b'\x0b\x00\x00\x00\x16\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00'
            # We will just toggle the relevant byte.
            # For now, we will use a simpler method if available, or note the complexity.
            # This tweak is complex and risky to implement via simple registry writes. A placeholder is safer.
            return True, "This tweak is for demonstration and is not implemented."
        except Exception as e:
            return False, f"Error setting full path in title: {e}"

    @staticmethod
    def set_transparency_effects(enable: bool):
        """Enable or disable transparency effects for the UI."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 1 if enable else 0)
            winreg.CloseKey(key)
            WinTweaks._broadcast_setting_change()
            return True, None
        except Exception as e:
            return False, f"Error setting transparency effects: {e}"

    @staticmethod
    def set_taskbar_alignment(align_left: bool):
        """Set taskbar alignment to Left or Center."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_SET_VALUE)
            # 0 = Left, 1 = Center
            winreg.SetValueEx(key, "TaskbarAl", 0, winreg.REG_DWORD, 0 if align_left else 1)
            winreg.CloseKey(key)
            WinTweaks._broadcast_setting_change()
            return True, None
        except Exception as e:
            return False, f"Error setting taskbar alignment: {e}"

    @staticmethod
    def set_animated_icons(enable: bool):
        """Enable or disable animated icons (example, not a real setting)."""
        # Animated icons are not directly supported via a simple registry key.
        return True, "This tweak is a placeholder and does not modify the system."

    @staticmethod
    def set_blur_effect(enable: bool):
        """Enable or disable blur effect (example, not a real setting)."""
        # Blur effects are not directly supported via a simple registry key.
        return True, "This tweak is a placeholder and does not modify the system."

    @staticmethod
    def set_aero_glass(enable: bool):
        """Enable or disable Aero Glass (example, not a real setting)."""
        # Aero Glass was a feature of Windows 7/Vista and is not a native toggle in Windows 10/11.
        # Third-party tools are required to achieve this effect.
        return True, "This tweak is a placeholder and does not modify the system."

    @staticmethod
    def clean_temporary_files(progress_callback=None):
        """Deletes files from user and Windows temp directories, with progress."""
        temp_dirs = [tempfile.gettempdir(), r"C:\Windows\Temp"]
        total_deleted_size = 0
        errors = []

        for directory in temp_dirs:
            if not os.path.exists(directory):
                continue
            
            items = os.listdir(directory)
            total_items = len(items)
            
            for i, item in enumerate(items):
                path = os.path.join(directory, item)
                try:
                    file_size = 0
                    if os.path.isfile(path) or os.path.islink(path):
                        file_size = os.path.getsize(path)
                        os.unlink(path)
                        total_deleted_size += file_size
                    elif os.path.isdir(path):
                        dir_size = 0
                        for dirpath, _, filenames in os.walk(path):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                dir_size += os.path.getsize(fp)
                        
                        file_size = dir_size
                        shutil.rmtree(path)
                        total_deleted_size += dir_size

                except (PermissionError, OSError) as e:
                    errors.append(f"Could not delete {path}: {e}")
                
                if progress_callback:
                    progress = (i + 1) / total_items * 100
                    progress_callback(progress, file_size)
        
        cleaned_mb = total_deleted_size / (1024 * 1024)
        return cleaned_mb, errors

    @staticmethod
    def get_startup_programs() -> List[StartupProgram]:
        """Gets a list of startup programs and their enabled/disabled status from HKCU and HKLM."""
        startup_items = []
        scopes = {
            'user': winreg.HKEY_CURRENT_USER,
            'machine': winreg.HKEY_LOCAL_MACHINE
        }

        for scope_name, hkey in scopes.items():
            run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            approved_key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

            try:
                with winreg.OpenKey(hkey, run_key_path) as run_key:
                    i = 0
                    while True:
                        try:
                            name, path, _ = winreg.EnumValue(run_key, i)
                            startup_items.append({'name': name, 'path': path, 'scope': scope_name, 'enabled': True})
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                logging.warning("Startup 'Run' key not found for %s.", scope_name)
            
            try:
                with winreg.OpenKey(hkey, approved_key_path) as approved_key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(approved_key, i)
                            # Find the corresponding item and update its status
                            for item in startup_items:
                                if item['name'] == name and item['scope'] == scope_name:
                                    # Value starting with 0x02 means disabled
                                    if value and value.startswith(b'\x02'):
                                        item['enabled'] = False
                                    break
                            i += 1
                        except OSError:
                            break
            except FileNotFoundError:
                logging.info("Startup 'StartupApproved' key not found for %s. All items assumed enabled.", scope_name)

        return startup_items

    @staticmethod
    def set_startup_program_state(name: str, scope: str, enabled: bool):
        """Enables or disables a startup program."""
        hkey = winreg.HKEY_CURRENT_USER if scope == 'user' else winreg.HKEY_LOCAL_MACHINE
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        
        try:
            with winreg.OpenKey(hkey, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    # To enable, delete the value from the 'StartupApproved' key.
                    winreg.DeleteValue(key, name)
                else:
                    # To disable, write a binary value starting with 0x02.
                    disabled_value = b'\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                    winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, disabled_value)
            return True, None
        except FileNotFoundError:
            return False, f"Could not find startup registry key for scope '{scope}'."
        except Exception as e:
            return False, f"Error modifying startup state for '{name}': {e}"

    @staticmethod
    def clear_browser_data():
        """Clears cache, cookies, and history for major browsers."""
        app_data = os.getenv('LOCALAPPDATA', '')
        browsers = {
            'Google Chrome': os.path.join(app_data, 'Google', 'Chrome', 'User Data'),
            'Microsoft Edge': os.path.join(app_data, 'Microsoft', 'Edge', 'User Data'),
            'Mozilla Firefox': os.path.join(os.getenv('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles')
        }
        
        total_deleted_size = 0
        errors = []

        data_types_to_clear = [
            'Cache', 'Code Cache', 'GPUCache', # Chromium
            'cookies.sqlite', # Firefox
            'History', 'Cookies' # Chromium (files)
        ]

        for name, path in browsers.items():
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    # Clear directories like 'Cache'
                    for d in dirs:
                        if d in data_types_to_clear:
                            dir_path = os.path.join(root, d)
                            try:
                                size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, _, filenames in os.walk(dir_path) for filename in filenames)
                                shutil.rmtree(dir_path, ignore_errors=True)
                                total_deleted_size += size
                            except Exception as e:
                                errors.append(f"Failed to delete {dir_path}: {e}")
                    # Clear files like 'History'
                    for f in files:
                        if f in data_types_to_clear:
                            file_path = os.path.join(root, f)
                            try:
                                size = os.path.getsize(file_path)
                                os.remove(file_path)
                                total_deleted_size += size
                            except Exception as e:
                                errors.append(f"Failed to delete {file_path}: {e}")

        cleaned_mb = total_deleted_size / (1024 * 1024)
        return cleaned_mb, errors

    @staticmethod
    def _check_windows_update_settings():
        """Checks if Windows Update is configured for automatic updates."""
        try:
            # Check for Windows Update settings in the registry
            # This key indicates how updates are handled (e.g., 2=Notify, 3=Auto, 4=Download and notify)
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update") as key:
                au_options = winreg.QueryValueEx(key, "AUOptions")[0]
                if au_options != 4: # 4 typically means "Download updates automatically and notify when they are ready to be installed"
                    return {'name': 'Windows Update Not Automatic', 'issue': f'Windows Update is not configured for automatic downloads and notifications (current setting: {au_options}).'}
        except FileNotFoundError:
            logging.warning("Windows Update registry key not found. Cannot determine settings.")
            return {'name': 'Windows Update Check Failed', 'issue': 'Could not determine Windows Update settings (registry key not found).'}
        except Exception as e:
            logging.error("Error checking Windows Update settings: %s", e)
            return {'name': 'Windows Update Check Failed', 'issue': f'Error checking Windows Update settings: {e}'}
        return None

    @staticmethod
    def scan_for_vulnerabilities():
        """Scans for common system vulnerabilities."""
        vulnerabilities = []

        # 1. Check if User Account Control (UAC) is enabled
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System") as key:
                if winreg.QueryValueEx(key, "EnableLUA")[0] != 1:
                    vulnerabilities.append({'name': 'UAC Disabled', 'issue': 'User Account Control (UAC) is disabled, reducing system security.'})
        except Exception as e:
            logging.error("Could not check UAC status: %s", e)
            vulnerabilities.append({'name': 'UAC Check Failed', 'issue': f'Could not determine UAC status: {e}'})

        # 2. Check Windows Update settings
        update_vulnerability = WinTweaks._check_windows_update_settings()
        if update_vulnerability:
            vulnerabilities.append(update_vulnerability)

        # 3. Check if Windows Firewall is enabled for the standard profile
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile") as key:
                if winreg.QueryValueEx(key, "EnableFirewall")[0] != 1:
                    vulnerabilities.append({'name': 'Firewall Disabled', 'issue': 'Windows Firewall is disabled for the standard network profile.'})
        except Exception as e:
            logging.error("Could not check Firewall status: %s", e)
            vulnerabilities.append({'name': 'Firewall Check Failed', 'issue': f'Could not determine Firewall status: {e}'})

        return vulnerabilities

    @staticmethod
    def get_local_drives() -> List[str]:
        """Gets a list of local, fixed drives (e.g., ['C:', 'D:'])."""
        drives = []
        partitions = psutil.disk_partitions()
        for p in partitions:
            if 'fixed' in p.opts and p.device:
                drives.append(p.device.rstrip('\\'))
        return drives

    @staticmethod
    def defragment_drive(drive_letter: str) -> Tuple[bool, str]:
        """Runs the Windows defragmentation utility on a given drive."""
        if not drive_letter or not drive_letter.endswith(':'):
            return False, "Invalid drive letter format. Expected 'C:'."
        
        try:
            # /U for progress, /V for verbose output
            result = subprocess.run(['defrag.exe', drive_letter, '/U', '/V'], capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            logging.info("Defragmentation output for %s:\n%s", drive_letter, result.stdout)
            return True, f"Defragmentation for drive {drive_letter} completed successfully."
        except FileNotFoundError:
            return False, "defrag.exe not found. This tool may not be available."
        except subprocess.CalledProcessError as e:
            logging.error("Defragmentation failed for %s:\n%s", drive_letter, e.stderr)
            return False, f"Defragmentation failed for drive {drive_letter}. See log for details."