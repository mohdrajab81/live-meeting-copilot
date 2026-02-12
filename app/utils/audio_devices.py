import sys
from typing import Any


def list_capture_devices() -> list[dict[str, Any]]:
    if sys.platform != "win32":
        return []

    try:
        import winreg
    except Exception:
        return []

    devices: list[dict[str, Any]] = []
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
    props_short = "{a45c254e-df1c-4efd-8020-67d146a850e0},2"
    props_friendly = "{b3f8fa53-0004-438e-9003-51a46e139bfc},6"
    props_endpoint = "{9c119480-ddc2-4954-a150-5bd240d454ad},10"

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            count = winreg.QueryInfoKey(root)[0]
            for idx in range(count):
                key_name = winreg.EnumKey(root, idx)
                state = None
                endpoint_id = f"{{0.0.1.00000000}}.{key_name}"
                short_name = ""
                friendly_name = ""
                try:
                    with winreg.OpenKey(root, key_name) as dev_key:
                        try:
                            state = int(winreg.QueryValueEx(dev_key, "DeviceState")[0])
                        except Exception:
                            state = None

                        with winreg.OpenKey(dev_key, "Properties") as pkey:
                            try:
                                short_name = str(winreg.QueryValueEx(pkey, props_short)[0] or "")
                            except Exception:
                                short_name = ""
                            try:
                                friendly_name = str(
                                    winreg.QueryValueEx(pkey, props_friendly)[0] or ""
                                )
                            except Exception:
                                friendly_name = ""
                            try:
                                endpoint_raw = str(
                                    winreg.QueryValueEx(pkey, props_endpoint)[0] or ""
                                )
                                if "MMDEVAPI\\" in endpoint_raw:
                                    endpoint_id = endpoint_raw.split("MMDEVAPI\\", 1)[1]
                            except Exception:
                                pass
                except Exception:
                    continue

                label = " / ".join([x for x in (short_name, friendly_name) if x]).strip()
                if not label:
                    label = key_name

                devices.append(
                    {
                        "id": endpoint_id,
                        "label": label,
                        "short_name": short_name,
                        "friendly_name": friendly_name,
                        "state": state,
                        "is_active": state == 1,
                    }
                )
    except Exception:
        return []

    active_devices = [d for d in devices if d.get("is_active")]
    active_devices.sort(key=lambda d: d.get("label", "").lower())
    return active_devices
