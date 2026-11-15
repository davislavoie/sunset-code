"""Observed cloud toward the sun from the GOES-East satellite, written onto every capture
(the forecast reads it on the pre shots; the dashboard shows it on all of them).

NOAA's public bucket noaa-goes19 (anonymous HTTPS), product ABI-L2-ACMC: the CONUS clear-sky mask,
2 km, a scan every 5 min, files ~4 min after the scan. The netCDF files are HDF5, so h5py reads them
through HTTP range requests (RangeFile): only the header and the chunks around Vermont, ~0.7 MB of 4 MB.
From the latest scan before the capture, the cloudy share of pixels (BCM) in:

  goes_over  within 10 km of the camera
  goes_near  sun bearing +/-30 deg, 5-40 km out
  goes_far   sun bearing +/-30 deg, 80-300 km out
  goes_fan   sun bearing +/-30 deg, 5-300 km out

On 513 sunset days (analysis/goes.md) these beat every forecast source for predicting the sunset.

Cloud height, product ABI-L2-ACHAC (CONUS cloud-top height, ~10 km, every 5 min, ~0.3 MB, day and night).
It sees the top layer only: low cloud under high cloud is missed. Per zone (over / near / far as above):

  goes_top_<zone>   median cloud-top height of the zone's cloudy pixels, km (None when it's clear)
  goes_high_<zone>  share of the zone's pixels with a cloud top at 6 km or higher (cirrus, the cloud that
                    lights up after sunset)
  goes_mid_<zone>   share with a cloud top at 2-6 km (mid-level cloud, altocumulus and the like)
  goes_low_<zone>   share with a cloud top under 2 km (low cloud that can block the horizon)

Cloud thickness, product ABI-L2-CODC (CONUS cloud optical depth, 2 km, every 5 min, ~1.2 MB for the rows the
zones need). It is only a thickness measurement while the sun is up: below 8 deg of sun the product switches
to an infrared method that never reads thick (analysis/thickness.md). So a capture taken with the sun under
DAY_ELEVATION gets the last daylight reading before it, and how old that reading is:

  goes_cod_<zone>   median optical depth of the zone's cloudy pixels (None when it's clear); under ~3.6 is
                    thin cloud the sun shines through, 23 and up a thick deck
  goes_cod_age      minutes from that scan to the capture

For the dashboard only: thickness did not improve the forecast (analysis/satellite_ideas.md).

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
HEIGHT_PRODUCT = "ABI-L2-ACHAC"
LATENCY = timedelta(minutes=5)  # a scan's file appears ~4 min after it starts
TIMEOUT = 15
FIELDS = ("goes_over", "goes_near", "goes_far", "goes_fan")
HIGH_KM, LOW_KM = 6.0, 2.0
COD_PRODUCT = "ABI-L2-CODC"
DAY_ELEVATION = 10  # deg of sun at the camera; the product's own switch is at 8, and the 1 h shot sits right on it
HEIGHT_FIELDS = tuple(f"goes_{k}_{z}" for z in ("over", "near", "far") for k in ("top", "high", "mid", "low"))


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


def scan_url(when, session=requests, product=PRODUCT):
    """URL of the latest scan that had landed by `when` (aware UTC datetime), or None."""
    cutoff = when - LATENCY
    keys = [k for hour in (cutoff - timedelta(hours=1), cutoff) for k in listing(f"{hour:%Y/%j/%H}", session, product)]
    keys = [k for k in keys if scan_start(k) <= cutoff]
    return f"{BUCKET}/{max(keys, key=scan_start)}" if keys else None


_listings = {}


def listing(hour, session=requests, product=PRODUCT):
    """Scan keys for one UTC hour ("YYYY/DDD/HH"). A finished hour never changes, so it's kept."""
    if (product, hour) in _listings:
        return _listings[product, hour]
    resp = session.get(f"{BUCKET}/?list-type=2&prefix={product}/{hour}/", timeout=TIMEOUT)
    resp.raise_for_status()
    keys = [k.split("</Key>")[0] for k in resp.text.split("<Key>")[1:]]
    if len(keys) >= 12:  # complete (12 scans an hour)
        _listings[product, hour] = keys
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
    import h5py  # only needed here; keeps the rest of ai_analysis importable without it

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


def zone_masks(lat, lon, lat0, lon0, azimuth, over_km=10):
    """Pixel masks for the zones: overhead, and the fan toward the sun (+/-30 deg) near, far and whole."""
    dy = (lat - lat0) * 111.2
    dx = (lon - lon0) * 111.2 * math.cos(math.radians(lat0))
    dist = np.hypot(dx, dy)
    off = np.abs((np.degrees(np.arctan2(dx, dy)) - azimuth + 180) % 360 - 180)
    fan = off <= 30
    return {"over": dist <= over_km, "near": fan & (dist >= 5) & (dist <= 40),
            "far": fan & (dist >= 80) & (dist <= 300), "fan": fan & (dist >= 5) & (dist <= 300)}


def zones(bcm, lat, lon, lat0, lon0, azimuth):
    """Cloudy share in each zone (FIELDS), None where a zone has no valid pixels."""
    masks = zone_masks(lat, lon, lat0, lon0, azimuth)
    return {f"goes_{k}": round(float(np.nanmean(bcm[m])), 3) if np.isfinite(bcm[m]).any() else None for k, m in masks.items()}


def height_window(url, session=requests):
    """(cloud-top height km, nan where clear, lat, lon) for the whole CONUS height scan (~0.3 MB)."""
    import h5py

    with h5py.File(RangeFile(url, session), "r") as h:
        scale = lambda v: h[v][:] * h[v].attrs["scale_factor"][0] + h[v].attrs["add_offset"][0]
        raw = h["HT"][:]
        ht = np.where(raw == h["HT"].attrs["_FillValue"][0], np.nan, raw * h["HT"].attrs["scale_factor"][0] / 1000)
        lat, lon = latlon_grid(scale("x"), scale("y"), dict(h["goes_imager_projection"].attrs))
    return ht, lat, lon


def heights(ht, lat, lon, lat0, lon0, azimuth):
    """HEIGHT_FIELDS from a cloud-top height grid (km, nan = clear). The pixels are ~10 km, so overhead
    takes the pixels within 15 km."""
    masks = zone_masks(lat, lon, lat0, lon0, azimuth, over_km=15)
    out = {}
    for z in ("over", "near", "far"):
        h = ht[masks[z] & np.isfinite(lat)]
        if not h.size:
            continue
        cloudy = h[np.isfinite(h)]
        out[f"goes_top_{z}"] = round(float(np.median(cloudy)), 2) if cloudy.size else None
        out[f"goes_high_{z}"] = round(float((cloudy >= HIGH_KM).sum() / h.size), 3)
        out[f"goes_mid_{z}"] = round(float(((cloudy >= LOW_KM) & (cloudy < HIGH_KM)).sum() / h.size), 3)
        out[f"goes_low_{z}"] = round(float((cloudy < LOW_KM).sum() / h.size), 3)
    return out


def observe(when, lat0, lon0, azimuth, session=requests):
    """Zone fractions from the latest scan by `when`, or None if there's no scan."""
    url = scan_url(when, session)
    return zones(*cloud_window(url, lat0, lon0, session), lat0, lon0, azimuth) if url else None


def observe_heights(when, lat0, lon0, azimuth, session=requests):
    """HEIGHT_FIELDS from the latest cloud-height scan by `when`, or None if there's no scan."""
    url = scan_url(when, session, HEIGHT_PRODUCT)
    return heights(*height_window(url, session), lat0, lon0, azimuth) if url else None


def last_daylight(when, lat0, lon0):
    """`when`, or the latest minute in the 3 h before it, with the sun at least DAY_ELEVATION up; None in the dark."""
    from astral import Observer
    from astral.sun import elevation

    observer = Observer(latitude=lat0, longitude=lon0)
    return next((t for t in (when - timedelta(minutes=m) for m in range(181)) if elevation(observer, t) >= DAY_ELEVATION), None)


def cod_window(url, lat0, lon0, azimuth, session=requests):
    """(optical depth, nan where missing; quality flags; lat; lon) over the rows the zones need, from one scan.
    COD is stored in chunks of full rows, so reading only those rows is what keeps this near 1 MB."""
    import h5py

    with h5py.File(RangeFile(url, session), "r") as h:
        scale = lambda v: h[v][:] * h[v].attrs["scale_factor"][0] + h[v].attrs["add_offset"][0]
        x, y = scale("x"), scale("y")
        proj = dict(h["goes_imager_projection"].attrs)
        lat, lon = latlon_grid(x[::20], y[::20], proj)  # coarse locate, as cloud_window
        d = (lat - lat0) ** 2 + ((lon - lon0) * math.cos(math.radians(lat0))) ** 2
        iy, ix = (20 * i for i in np.unravel_index(np.nanargmin(d), d.shape))
        ys, xs = slice(max(0, iy - 200), iy + 200), slice(max(0, ix - 200), ix + 200)
        lat, lon = latlon_grid(x[xs], y[ys], proj)
        rows = np.flatnonzero(np.logical_or.reduce(list(zone_masks(lat, lon, lat0, lon0, azimuth).values())).any(axis=1))
        r = slice(ys.start + rows[0], ys.start + rows[-1] + 1)
        raw, dqf = h["COD"][r, xs], h["DQF"][r, xs]
        cod = np.where(raw == h["COD"].attrs["_FillValue"][0], np.nan, raw * h["COD"].attrs["scale_factor"][0])
    return cod, dqf, lat[rows[0]:rows[-1] + 1], lon[rows[0]:rows[-1] + 1]


def thickness(cod, dqf, lat, lon, lat0, lon0, azimuth):
    """goes_cod_<zone>: median optical depth of each zone's cloudy pixels, None where it has none. Only pixels
    from the daylight method (DQF bit 0 clear) count."""
    masks = zone_masks(lat, lon, lat0, lon0, azimuth)
    cloudy = np.isfinite(cod) & (cod > 0) & (dqf & 1 == 0)
    return {f"goes_cod_{z}": round(float(np.median(cod[masks[z] & cloudy])), 2) if (masks[z] & cloudy).any() else None
            for z in ("over", "near", "far")}


_thickness = {}  # every capture after the sun gets low shares one scan, so a day's reading is kept (a few numbers each)


def observe_thickness(when, lat0, lon0, azimuth, session=requests):
    """goes_cod_* from the last daylight scan by `when`, plus its age; None in the dark or with no scan."""
    t = last_daylight(when, lat0, lon0)
    url = t and scan_url(t, session, COD_PRODUCT)
    if not url:
        return None
    key = (url, lat0, lon0, azimuth)
    if key not in _thickness:
        _thickness[key] = thickness(*cod_window(url, lat0, lon0, azimuth, session), lat0, lon0, azimuth)
    return {**_thickness[key], "goes_cod_age": round((when - scan_start(url)).total_seconds() / 60, 1)}


def fill(client, camera, recent="2d", since=None, before=None):
    """Add GOES cloud, cloud height and cloud thickness fields to captures lacking them. Returns how many got any."""
    from sunset_code.helpers.open_metro_weater_api import sun_bearing

    from .weather import camera_config

    todo = [p for p in store.captures(client, camera, recent=None if since or before else recent, since=since, before=before)
            if p.get("goes_fan") is None or p.get("goes_high_far") is None or p.get("goes_cod_age") is None]
    if not todo:
        return 0
    config = camera_config(camera)
    lat, lon, mode = float(config["LAT"]), float(config["LON"]), config.get("MODE", "sunset")
    session, writes, done = requests.Session(), [], 0
    for i, p in enumerate(todo, 1):
        when, bearing, got = store.parse_time(p), sun_bearing(store.local_date(p), lat, lon, mode), {}
        for what, missing, read in (("cloud", p.get("goes_fan") is None, observe),
                                    ("cloud height", p.get("goes_high_far") is None, observe_heights),
                                    ("cloud thickness", p.get("goes_cod_age") is None, observe_thickness)):
            if not missing:
                continue
            try:
                got.update(read(when, lat, lon, bearing, session) or {})
            except Exception as e:  # S3 slow or down, odd file: try again next pass
                log.warning("%s %s: no GOES %s reading (%s)", camera, p["time"], what, e)
        fields = {k: v for k, v in got.items() if v is not None}
        if fields:
            writes.append(store.field_point(p, fields))
        if len(writes) >= 50:  # save as we go: a backfill of history takes hours
            client.write_points(writes)
            done, writes = done + len(writes), []
            log.info("%s: GOES %d of %d captures", camera, i, len(todo))
    if writes:
        client.write_points(writes)
        done += len(writes)
    log.info("%s: GOES cloud added to %d of %d captures", camera, done, len(todo))
    return done
