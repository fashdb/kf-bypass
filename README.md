

```bash
pip install git+https://github.com/fashdb/kf-bypass
```

```
from kf_bypass import Scraper

s = Scraper()
r = s.get("https://kiwifarms.net")
print(r.status_code)
```
