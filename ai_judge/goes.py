"""Observed cloud toward the sun from the GOES-East satellite, written onto pre-sunset captures.

NOAA's public bucket noaa-goes19 (anonymous HTTPS), product ABI-L2-ACMC: the CONUS clear-sky mask,
2 km, a scan every 5 min, files ~4 min after the scan. The netCDF files are HDF5, so h5py reads them
through HTTP range requests (RangeFile): only the header and the chunks around Vermont, ~0.7 MB of 4 MB.
From the latest scan before the capture, the cloudy share of pixels (BCM) in:

  goes_over  within 10 km of the camera
  goes_near  sun bearing +/-30 deg, 5-40 km out
  goes_far   sun bearing +/-30 deg, 80-300 km out
  goes_fan   sun bearing +/-30 deg, 5-300 km out

On 513 sunset days (analysis/goes.md) these beat every forecast source for predicting the sunset.
Anything unavailable (S3 down, a missing scan) is skipped and retried next pass.
"""

import io
import logging
import math
from datetime import datetime, timedelta, timezone

import numpy as np
import requests

from . import store

log = logging.getLogger(__name__)

BUCKET = "https://noaa-goes19.s3.amazonaws.com"
PRODUCT = "ABI-L2-ACMC"
LATENCY = timedelta(minutes=5)  # a scan's file appears ~4 min after it starts
TIMEOUT = 15
FIELDS = ("goes_over", "goes_near", "goes_far", "goes_fan")


class RangeFile(io.RawIOBase):
    """Read-only file over HTTP range requests with a block cache (h5py accepts file-like objects)."""

    BLOCK = 256 * 1024

    def __init__(self, url, session=requests):
        self.url, self.session, self.pos, self.blocks, self.fetched = url, session, 0, {}, 0
        self.size = None
        self.block(0)  # its Content-Range gives the size: no separate HEAD round trip

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def block(self, i):
        if i not in self.blocks:
            lo = i * self.BLOCK
            hi = lo + self.BLOCK if self.size is None else min(self.size, lo + self.BLOCK)
            resp = self.session.get(self.url, headers={"Range": f"bytes={lo}-{hi - 1}"}, timeout=TIMEOUT)
            resp.raise_for_status()
            if self.size is None:
                self.size = int(resp.headers["Content-Range"].rsplit("/", 1)[1])
            self.blocks[i] = resp.content
            self.fetched += len(resp.content)
        return self.blocks[i]

    def readinto(self, b):
        n = max(0, min(len(b), self.size - self.pos))
        out, pos = bytearray(), self.pos
        while len(out) < n:
            blk = self.block(pos // self.BLOCK)
            piece = blk[pos % self.BLOCK: pos % self.BLOCK + n - len(out)]
            out += piece
            pos += len(piece)
        b[:n] = out
        self.pos += n
        return n


def scan_start(key):
    return datetime.strptime(key.split("_s")[1][:13], "%Y%j%H%M%S").replace(tzinfo=timezone.utc)


def scan_url(when, session=requests):
    """URL of the latest scan that had landed by `when` (aware UTC datetime), or None."""
    cutoff = when - LATENCY
    keys = [k for hour in (cutoff - timedelta(hours=1), cutoff) for k in listing(f"{hour:%Y/%j/%H}", session)]
    keys = [k for k in keys if scan_start(k) <= cutoff]
    return f"{BUCKET}/{max(keys, key=scan_start)}" if keys else None


_listings = {}


def listing(hour, session=requests):
    """Scan keys for one UTC hour ("YYYY/DDD/HH"). A finished hour never changes, so it's kept."""
    if hour in _listings:
        return _listings[hour]
    resp = session.get(f"{BUCKET}/?list-type=2&prefix={PRODUCT}/{hour}/", timeout=TIMEOUT)
    resp.raise_for_status()
    keys = [k.split("</Key>")[0] for k in resp.text.split("<Key>")[1:]]
    if len(keys) >= 12:  # complete (12 scans an hour)
        _listings[hour] = keys
    return keys


def latlon_grid(x, y, proj):
    """GOES fixed-grid scan angles (radians) -> lat/lon degrees (GOES-R PUG vol. 4, 7.1.2.8.1)."""
    H = proj["perspective_point_height"][0] + proj["semi_major_axis"][0]
    a, b = proj["semi_major_axis"][0], proj["semi_minor_axis"][0]
    lon0 = math.radians(proj["longitude_of_projection_origin"][0])
    x, y = np.meshgrid(x, y)
    ca = np.sin(x) ** 2 + np.cos(x) ** 2 * (np.cos(y) ** 2 + a ** 2 / b ** 2 * np.sin(y) ** 2)
    cb = -2 * H * np.cos(x) * np.cos(y)
    with np.errstate(invalid="ignore"):
        rs = (-cb - np.sqrt(cb ** 2 - 4 * ca * (H ** 2 - a ** 2))) / (2 * ca)
    sx, sy, sz = rs * np.cos(x) * np.cos(y), -rs * np.sin(x), rs * np.cos(x) * np.sin(y)
    lat = np.degrees(np.arctan(a ** 2 / b ** 2 * sz / np.sqrt((H - sx) ** 2 + sy ** 2)))
    return lat, np.degrees(lon0 - np.arctan(sy / (H - sx)))


def cloud_window(url, lat0, lon0, session=requests):
    """(BCM cloud mask 0/1/nan, lat, lon) for a ~400 km window around the camera, from one scan."""
    import h5py  # only needed here; keeps the rest of ai_judge importable without it

    with h5py.File(RangeFile(url, session), "r") as h:
        scale = lambda v: h[v][:] * h[v].attrs["scale_factor"][0] + h[v].attrs["add_offset"][0]
        x, y = scale("x"), scale("y")
        proj = dict(h["goes_imager_projection"].attrs)
        lat, lon = latlon_grid(x[::20], y[::20], proj)  # coarse locate, then a +/-200 px window
        d = (lat - lat0) ** 2 + ((lon - lon0) * math.cos(math.radians(lat0))) ** 2
        iy, ix = (20 * i for i in np.unravel_index(np.nanargmin(d), d.shape))
        ys, xs = slice(max(0, iy - 200), iy + 200), slice(max(0, ix - 200), ix + 200)
        bcm = h["BCM"][ys, xs].astype(float)
        bcm[bcm > 1] = np.nan  # fill / off-disk
        lat, lon = latlon_grid(x[xs], y[ys], proj)
    return bcm, lat, lon


def zones(bcm, lat, lon, lat0, lon0, azimuth):
    """Cloudy share in each zone (FIELDS), None where a zone has no valid pixels."""
    dy = (lat - lat0) * 111.2
    dx = (lon - lon0) * 111.2 * math.cos(math.radians(lat0))
    dist = np.hypot(dx, dy)
    off = np.abs((np.degrees(np.arctan2(dx, dy)) - azimuth + 180) % 360 - 180)
    fan = off <= 30
    masks = {"goes_over": dist <= 10, "goes_near": fan & (dist >= 5) & (dist <= 40),
             "goes_far": fan & (dist >= 80) & (dist <= 300), "goes_fan": fan & (dist >= 5) & (dist <= 300)}
    return {k: round(float(np.nanmean(bcm[m])), 3) if np.isfinite(bcm[m]).any() else None for k, m in masks.items()}


def observe(when, lat0, lon0, azimuth, session=requests):
    """Zone fractions from the latest scan by `when`, or None if there's no scan."""
    url = scan_url(when, session)
    return zones(*cloud_window(url, lat0, lon0, session), lat0, lon0, azimuth) if url else None


def fill(client, camera, recent="2d", since=None, before=None):
    """Add GOES fields to pre-sunset (pre-sunrise) shots lacking them. Returns how many got them."""
    from sunset_code.helpers.open_metro_weater_api import sun_bearing

    from .predict import label_of
    from .weather import camera_config

    todo = [p for p in store.captures(client, camera, recent=None if since or before else recent, since=since, before=before)
            if label_of(p) and p.get("goes_fan") is None]
    if not todo:
        return 0
    config = camera_config(camera)
    lat, lon, mode = float(config["LAT"]), float(config["LON"]), config.get("MODE", "sunset")
    session, writes = requests.Session(), []
    for p in todo:
        try:
            got = observe(store.parse_time(p), lat, lon, sun_bearing(store.local_date(p), lat, lon, mode), session)
        except Exception as e:  # S3 slow or down, odd file: try again next pass
            log.warning("%s %s: no GOES reading (%s)", camera, p["time"], e)
            continue
        fields = {k: v for k, v in (got or {}).items() if v is not None}
        if fields:
            writes.append(store.field_point(p, fields))
    if writes:
        client.write_points(writes, batch_size=500)
    log.info("%s: GOES cloud added to %d of %d pre shots", camera, len(writes), len(todo))
    return len(writes)
