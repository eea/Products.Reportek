"""The answers of the registry, shared by the pods through Valkey/Redis.

Every pod keeps the answers of the registry in its own memory (plone.memoize),
so a user that reaches a pod that did not see them yet makes the pod ask the
registry again. This cache sits behind the memory of the pod: a pod that misses
asks Valkey before it asks the registry.

The answers decide what a user can access, so the cache keeps what the memory
of the pod keeps, no more:

* the key holds the window (time // interval) of the answer, as the key of the
  memory of the pod does, and the entry expires with the window: an answer is
  never older than the interval, in a pod or in Valkey;
* only the answers that the registry gave are stored, never a failure;
* an entry is signed (HMAC, with a key derived from SESSION_SECRET): what cannot
  be verified is a miss;
* Valkey that does not answer, or answers late, is a miss: the pod asks the
  registry as it did before, and after a few errors Valkey is left alone for a
  while. Nothing waits for Valkey for longer than a fraction of a second.

It is off unless REGISTRY_SHARED_CACHE is set. The address is
REGISTRY_CACHE_URL, or REDIS_URL, the Valkey of the sessions.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import zlib
from time import sleep, time

logger = logging.getLogger("Reportek")

KEY_PREFIX = "reportek:regcache:v1"
FORMAT = b"1"
SIGNATURE_SIZE = hashlib.sha256().digest_size
# seconds to connect to Valkey and to wait for it
TIMEOUT = 0.1
# errors in a row that leave Valkey alone, and for how many seconds
BREAKER_ERRORS = 3
BREAKER_SECONDS = 15
# the pod that asks the registry holds this lock, the others wait for the
# answer instead of asking too (seconds). A Valkey that answers slowly but
# within TIMEOUT is not an error: a lookup can wait for it a second at most,
# a DNS that does not answer is not bounded by TIMEOUT.
LOCK_SECONDS = 10
WAIT_SECONDS = 0.5
WAIT_STEP = 0.05

RELEASE_LOCK = (
    "if redis.call('get', KEYS[1]) == ARGV[1] then "
    "return redis.call('del', KEYS[1]) else return 0 end"
)

MISS = object()
# Valkey did not answer
ERROR = object()


def _enabled_in_env():
    return os.environ.get("REGISTRY_SHARED_CACHE", "").lower() in ("1", "true", "yes")


class SharedCache:
    """Gets what the registry answered from Valkey, or asks the registry."""

    def __init__(self, client=None):
        # a client given by the caller, in tests
        self._given = client
        self._client = None
        self._client_url = None
        self._lock = threading.Lock()
        self._errors = 0
        self._left_alone_until = 0
        # an object with record(name, outcome, seconds), see LookupStats
        self.stats = None

    # -- settings

    def enabled(self):
        if not self._secret():
            return False
        return self._given is not None or (_enabled_in_env() and bool(self._url()))

    def _url(self):
        return os.environ.get("REGISTRY_CACHE_URL") or os.environ.get("REDIS_URL")

    def _secret(self):
        secret = os.environ.get("SESSION_SECRET")
        if not secret:
            return None
        return hmac.new(
            secret.encode(), b"reportek-registry-cache-v1", hashlib.sha256
        ).digest()

    def _valkey(self):
        if self._given is not None:
            return self._given
        url = self._url()
        with self._lock:
            if self._client is None or self._client_url != url:
                import redis

                self._client = redis.Redis.from_url(
                    url,
                    socket_connect_timeout=TIMEOUT,
                    socket_timeout=TIMEOUT,
                    retry_on_timeout=False,
                )
                self._client_url = url
            return self._client

    # -- keys and values

    def _key(self, name, parts):
        digest = hashlib.sha256(
            json.dumps(parts, sort_keys=True, default=str).encode()
        ).hexdigest()
        return "%s:%s:%s" % (KEY_PREFIX, name, digest[:40])

    def _sign(self, key, body):
        return hmac.new(
            self._secret() or b"", key.encode() + b"\n" + body, hashlib.sha256
        ).digest()

    def _pack(self, key, value, fetched_at):
        body = zlib.compress(
            json.dumps({"t": fetched_at, "v": value}, separators=(",", ":")).encode()
        )
        return FORMAT + self._sign(key, body) + body

    def _unpack(self, key, raw, max_age):
        """The value of a stored entry, MISS if it cannot be trusted."""
        if not raw or raw[:1] != FORMAT:
            return MISS
        signature, body = raw[1 : 1 + SIGNATURE_SIZE], raw[1 + SIGNATURE_SIZE :]
        if not hmac.compare_digest(signature, self._sign(key, body)):
            logger.warning("Registry cache: an entry with a wrong signature")
            return MISS
        try:
            entry = json.loads(zlib.decompress(body))
            if time() - entry["t"] > max_age:
                return MISS
            return entry["v"]
        except Exception:
            return MISS

    # -- Valkey, without ever failing the caller

    def _record(self, name, outcome):
        if self.stats is not None:
            self.stats.record(name + " (valkey)", outcome)

    def _usable(self):
        return time() >= self._left_alone_until

    def _failed(self, what, exc):
        self._errors += 1
        if self._errors >= BREAKER_ERRORS:
            if self._usable():
                logger.warning(
                    "Registry cache: Valkey is left alone for %s seconds (%s: %r)",
                    BREAKER_SECONDS,
                    what,
                    exc,
                )
            self._left_alone_until = time() + BREAKER_SECONDS
        else:
            logger.debug("Registry cache: Valkey %s failed: %r", what, exc)

    def _worked(self):
        self._errors = 0

    def _call(self, what, name, function, default=None):
        """Calls Valkey; an error or a Valkey that is left alone gives default."""
        if not self._usable():
            return default
        try:
            result = function(self._valkey())
        except Exception as e:
            self._failed(what, e)
            self._record(name, "failure")
            return default
        self._worked()
        return result

    def _get(self, name, key, max_age):
        raw = self._call("get", name, lambda c: c.get(key), default=ERROR)
        if raw is ERROR:
            return ERROR
        return self._unpack(key, raw, max_age)

    def _set(self, name, key, value, ttl, fetched_at):
        try:
            packed = self._pack(key, value, fetched_at)
        except Exception as e:
            # the registry answered: the lookup does not fail for what cannot be shared
            logger.warning("Registry cache: %s cannot be stored (%r)", name, e)
            return
        self._call("set", name, lambda c: c.set(key, packed, ex=max(1, int(ttl))))

    def _take_lock(self, name, key, token):
        """True if this pod holds the lock, False if another does, None on error."""
        taken = self._call(
            "lock",
            name,
            lambda c: bool(c.set(key + ":lock", token, nx=True, ex=LOCK_SECONDS)),
        )
        return taken

    def _release_lock(self, name, key, token):
        """Deletes the lock if it is ours: a lock that expired may be another's."""
        self._call(
            "unlock",
            name,
            lambda c: c.eval(RELEASE_LOCK, 1, key + ":lock", token),
        )

    # -- the lookup

    def fetch(self, name, parts, ttl, load):
        """The answer of the registry for parts, from Valkey if a pod has it.

        parts identify the answer, with its window. ttl is the seconds that the
        answer is kept: no more than its window. load() asks the registry and
        returns (value, stored): stored says that the registry answered and the
        value can be shared. A failure of the registry is an exception of load(),
        it is not stored and it reaches the caller.
        """
        if not self.enabled():
            return load()[0]
        key = self._key(name, parts)
        value = self._lookup(name, key, ttl)
        if value is ERROR:
            # Valkey does not work: no lock, no store, one error for this lookup
            return load()[0]
        if value is not MISS:
            return value

        token = secrets.token_hex(16)
        locked = self._take_lock(name, key, token)
        try:
            if locked is False and self._usable():
                value = self._wait_for(name, key, ttl)
                if value is not MISS:
                    return value
            # the answer is as old as the moment that the registry was asked
            asked_at = time()
            value, stored = load()
            if stored:
                self._set(name, key, value, ttl, asked_at)
            return value
        finally:
            if locked:
                self._release_lock(name, key, token)

    def _lookup(self, name, key, ttl):
        self._record(name, "lookup")
        value = self._get(name, key, ttl)
        if value is MISS:
            self._record(name, "miss")
        return value

    def has(self, name, parts, ttl):
        """Does Valkey hold the answer (a lookup of the pod would not ask the registry)?

        An error is no: the lookup then goes on as without Valkey."""
        if not self.enabled():
            return False
        value = self._get(name, self._key(name, parts), ttl)
        return value is not MISS and value is not ERROR

    def _wait_for(self, name, key, ttl):
        """Waits a moment for the pod that asks the registry."""
        deadline = time() + WAIT_SECONDS
        while time() < deadline and self._usable():
            sleep(WAIT_STEP)
            value = self._get(name, key, ttl)
            if value is not MISS and value is not ERROR:
                return value
            if value is ERROR:
                break
        return MISS


shared_cache = SharedCache()
