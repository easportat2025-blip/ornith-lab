# -*- coding: utf-8 -*-
"""push_debug.py - push kernel va in NOI DUNG LOI THAT (CLI che message body)."""
import sys

from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()
slug = sys.argv[1]
dirn = sys.argv[2]
try:
    api.kernels_push(slug, dirn)
    print("PUSH OK", slug)
except Exception as e:
    print("LOI:", type(e).__name__, str(e)[:400])
    r = getattr(e, "response", None)
    if r is not None:
        try:
            print("BODY:", r.text[:1500])
        except Exception:
            pass
