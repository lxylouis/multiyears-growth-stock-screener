# JSON 缓存读取模式

## The Double-Load Bug

### ❌ Antipattern (found in all three data_*.py modules)

```python
if os.path.exists(cache_p) and (time.time()-os.path.getmtime(cache_p))/86400 < 7:
    with open(cache_p) as f:
        print(f"📂 使用缓存 ({len(json.load(f))}只)")  # ← first load, file pointer exhausted
        return json.load(f)                            # ← second load on empty → JSONDecodeError
```

`json.load(f)` reads the entire file and advances the file pointer to EOF. A second `json.load(f)` on the same handle reads an empty string → `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.

### ✅ Correct Pattern

```python
if os.path.exists(cache_p) and os.path.getsize(cache_p) > 0 \
   and (time.time()-os.path.getmtime(cache_p))/86400 < 7:
    try:
        with open(cache_p) as f:
            data = json.load(f)         # load ONCE into a variable
            if data:                    # guard against empty dict
                print(f"📂 使用缓存 ({len(data)}只)")  # reuse variable
                return data
    except (json.JSONDecodeError, ValueError):         # corrupted file
        print(f"⚠️  缓存损坏，重新下载")
        os.remove(cache_p)
```

### Defenses

1. **Load once** — always assign `json.load(f)` to a variable before any use.
2. **File size check** — `os.path.getsize(cache_p) > 0` catches empty files before opening.
3. **try/except** — wraps `json.JSONDecodeError` and `ValueError` so a corrupted file triggers automatic cache rebuild instead of a crash.
4. **Consistent pattern** — ALL six cache-reading sites in three data modules use the same fix:
   - `lib/data_cn.py` ×2 (price + revenue)
   - `lib/data_hk.py` ×2 (price + revenue)
   - `lib/data_us.py` ×2 (price + revenue)

## Cache File Locations

| Module | Cache File | Lifecycle |
|--------|-----------|-----------|
| `data_us.py` | `march_closes.json` | Price data, 7 days |
| `data_us.py` | `us_revenue.json` | Revenue data, 7 days |
| `data_hk.py` | `march_closes.json` | Price data, 7 days |
| `data_hk.py` | `hk_revenue.json` | Revenue data, 7 days |
| `data_cn.py` | `march_closes.json` | Price data, 7 days |
| `data_cn.py` | `revenue_data.json` | Revenue data, 7 days |

All under `~/.hermes/stock_cache/<index_name>_analysis/`.

## Why This Bug Happens

The subagent pattern was: copy-paste from one data module to another, forgetting that `json.load(f)` mutates state (consumes the file handle). The bug is invisible during the first run (no cache → download path) and only surfaces on the second run (cache exists → read path). It's a **latent bug** that passes initial QA.
