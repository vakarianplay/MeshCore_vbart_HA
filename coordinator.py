from __future__ import annotations

from datetime import timedelta, datetime, timezone
import logging
import ssl
import aiohttp

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BASE_URL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    CONF_INSECURE_TLS,
    CONF_BLOCKS,
    DEFAULT_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    ALL_BLOCKS,
)

_LOGGER = logging.getLogger(__name__)

# --- anti-429 tuning ---
NEIGHBOR_CACHE_TTL_SEC = 24 * 3600
MAX_ENRICH_PER_UPDATE = 2          # не больше 2 новых соседей за цикл
MESHCORETEL_BACKOFF_SEC = 30 * 60  # 30 минут пауза после 429

def _normalize_blocks(value):
    if isinstance(value, dict):
        return [k for k, v in value.items() if v]
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, list):
        return value
    return ALL_BLOCKS

class MeshcoreCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        cfg = {**entry.data, **entry.options}

        self.base_url = cfg[CONF_BASE_URL].rstrip("/")
        self.password = cfg[CONF_PASSWORD]
        self.verify_ssl = cfg.get(CONF_VERIFY_SSL, False)
        self.insecure_tls = cfg.get(CONF_INSECURE_TLS, True)
        self.blocks = _normalize_blocks(cfg.get(CONF_BLOCKS, ALL_BLOCKS))

        scan_interval = max(int(cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)), MIN_SCAN_INTERVAL)

        # кеш обогащения соседей: full_id -> {"observer", "model", "last_message_at", "_ts"}
        self._neighbors_cache: dict[str, dict] = {}
        self._meshcoretel_backoff_until: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            name="meshcore_observer",
            update_interval=timedelta(seconds=scan_interval),
        )

    def _build_ssl_for_local(self):
        """SSL policy for local meshcore node without blocking load_default_certs."""
        if self.base_url.startswith("http://"):
            return None  # TLS не нужен

        if self.verify_ssl:
            return True  # стандартная проверка aiohttp

        # Без create_default_context -> без warning про blocking load_default_certs
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        if self.insecure_tls:
            try:
                ctx.minimum_version = ssl.TLSVersion.TLSv1
            except Exception:
                pass
            try:
                ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
            except Exception:
                pass

        return ctx

    def _cache_get(self, full_id: str):
        item = self._neighbors_cache.get(full_id)
        if not item:
            return None
        ts = item.get("_ts", 0)
        if (datetime.now(timezone.utc).timestamp() - ts) > NEIGHBOR_CACHE_TTL_SEC:
            return None
        return item

    def _cache_put(self, full_id: str, observer=None, model=None, last_message_at=None):
        self._neighbors_cache[full_id] = {
            "observer": observer,
            "model": model,
            "last_message_at": last_message_at,
            "_ts": datetime.now(timezone.utc).timestamp(),
        }

    def _in_backoff(self):
        return self._meshcoretel_backoff_until and datetime.now(timezone.utc) < self._meshcoretel_backoff_until

    async def _safe_get_json(self, session: aiohttp.ClientSession, url: str, ssl_opt=True):
        """Safe GET for meshcoretel. Returns dict or None."""
        if self._in_backoff():
            return None

        headers = {
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Referer": "https://meshcoretel.ru/",
            "Origin": "https://meshcoretel.ru",
            "Cache-Control": "no-cache",
        }

        try:
            async with session.get(url, headers=headers, ssl=ssl_opt) as resp:
                text = await resp.text()

                if resp.status == 429:
                    self._meshcoretel_backoff_until = datetime.now(timezone.utc) + timedelta(seconds=MESHCORETEL_BACKOFF_SEC)
                    _LOGGER.warning("meshcoretel rate limit (429). Backoff until %s", self._meshcoretel_backoff_until.isoformat())
                    return None

                if resp.status != 200:
                    _LOGGER.debug("meshcoretel %s -> HTTP %s", url, resp.status)
                    return None

                # иногда приходит HTML/защита вместо JSON
                txt = text.lstrip()
                if not (txt.startswith("{") or txt.startswith("[")):
                    _LOGGER.debug("meshcoretel non-json response for %s: %s", url, text[:120])
                    return None

                return await resp.json(content_type=None)

        except Exception as e:
            _LOGGER.debug("meshcoretel request failed %s: %s", url, e)
            return None

    async def _login(self, session: aiohttp.ClientSession, ssl_opt):
        url = f"{self.base_url}/login"
        headers = {"Content-Type": "text/plain"}

        async with session.post(
            url,
            data=self.password.encode("utf-8"),
            headers=headers,
            ssl=ssl_opt,
        ) as resp:
            body = await resp.text()
            resp.raise_for_status()

            ctype = resp.headers.get("Content-Type", "")
            if "application/json" in ctype:
                payload = await resp.json(content_type=None)
                token = payload.get("token") or payload.get("access_token") or ""
            else:
                token = body.strip().strip('"')

            if not token:
                raise UpdateFailed("Empty token from /login")
            return token

    async def _fetch_stats(self, session: aiohttp.ClientSession, token: str, ssl_opt):
        url = f"{self.base_url}/api/stats"
        headers = {"X-Auth-Token": token}

        async with session.get(url, headers=headers, ssl=ssl_opt) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            if not isinstance(data, dict):
                raise UpdateFailed("Stats response is not a JSON object")
            return data

    async def _enrich_neighbors(self, session: aiohttp.ClientSession, neighbors: list[dict]):
        result = []
        enriched_this_cycle = 0

        for n in neighbors:
            full_id = n.get("full_id")
            item = {
                "id": n.get("id"),
                "full_id": full_id,
                "observer": None,
                "model": None,
                "last_message_at": None,
                "snr_db": n.get("snr_db"),
            }

            # 1) сначала из кеша
            if full_id:
                cached = self._cache_get(full_id)
                if cached:
                    item["observer"] = cached.get("observer")
                    item["model"] = cached.get("model")
                    item["last_message_at"] = cached.get("last_message_at")

            # 2) если данных нет и лимит цикла не исчерпан и нет backoff
            need_enrich = (not item["observer"] or not item["last_message_at"])
            if full_id and need_enrich and not self._in_backoff() and enriched_this_cycle < MAX_ENRICH_PER_UPDATE:
                # primary
                d1 = await self._safe_get_json(session, f"https://meshcoretel.ru/api/observers/{full_id}", ssl_opt=True)
                if isinstance(d1, dict):
                    item["observer"] = item["observer"] or d1.get("observer") or d1.get("name")
                    item["model"] = item["model"] or d1.get("model")
                    item["last_message_at"] = item["last_message_at"] or d1.get("last_message_at") or d1.get("last_seen_at")

                # fallback
                if not item["observer"] or not item["last_message_at"]:
                    d2 = await self._safe_get_json(
                        session,
                        f"https://meshcoretel.ru/api/nodes/{full_id}/repeater-dashboard",
                        ssl_opt=True,
                    )
                    if isinstance(d2, dict):
                        rep = d2.get("repeater", {})
                        item["observer"] = item["observer"] or rep.get("name") or d2.get("name")
                        item["model"] = item["model"] or rep.get("model") or d2.get("model")
                        item["last_message_at"] = item["last_message_at"] or rep.get("last_seen_at") or d2.get("last_seen_at")

                # кешируем, если что-то получили
                if item["observer"] or item["model"] or item["last_message_at"]:
                    self._cache_put(
                        full_id,
                        observer=item["observer"],
                        model=item["model"],
                        last_message_at=item["last_message_at"],
                    )

                enriched_this_cycle += 1

            result.append(item)

        return result

    async def _async_update_data(self):
        try:
            timeout = aiohttp.ClientTimeout(total=25)
            ssl_local = self._build_ssl_for_local()

            async with aiohttp.ClientSession(timeout=timeout) as session:
                token = await self._login(session, ssl_local)
                stats = await self._fetch_stats(session, token, ssl_local)

                filtered = {}
                for block in self.blocks:
                    if block in stats:
                        filtered[block] = stats.get(block)

                if "neighbors_detail" in self.blocks and isinstance(stats.get("neighbors_detail"), list):
                    filtered["neighbors_detail"] = await self._enrich_neighbors(
                        session, stats.get("neighbors_detail", [])
                    )

                return filtered

        except Exception as err:
            raise UpdateFailed(f"Meshcore update failed: {err}") from err