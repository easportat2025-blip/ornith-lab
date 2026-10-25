# -*- coding: utf-8 -*-
"""dummy_2048.py - policy GT cho T20_2048 (trich tu harness).
Doi cdp_eval -> _page_state (Colab dung Playwright evaluate).
"""
import json


def _slide(g, m):
    """Simulate one 2048 move (left/down/right/up) -> new grid or None if no change."""
    n = len(g)

    def slide(row):
        a = [v for v in row if v]
        for i in range(len(a) - 1, 0, -1):
            if a[i] == a[i - 1]:
                a[i] *= 2
                a[i - 1] = 0
        while len(a) < n:
            a.append(0)
        return a

    ng = [row[:] for row in g]
    if m == "left":
        ng = [slide(r) for r in g]
    elif m == "right":
        ng = [slide(r[::-1])[::-1] for r in g]
    elif m == "up":
        for c in range(n):
            col = slide([g[r][c] for r in range(n)])
            for r in range(n):
                ng[r][c] = col[r]
    elif m == "down":
        for c in range(n):
            col = slide([g[r][c] for r in range(n)][::-1])[::-1]
            for r in range(n):
                ng[r][c] = col[r]
    if ng == g:
        return None
    return ng


# Demo policy cho cac app co BIEN NGAU NHIEN (TASK-28 v2): doc gia tri + toa do
# truc tiep tu trang (qua CDP) roi thao tac THAT -> sinh ra data co y nghia.


class Dummy2048:
    """Scripted policy for T20_2048: read the grid over CDP, pick a good move.

    Proves the harness (obs -> action -> real keys -> reward) with NO model.
    """

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        grid = None
        try:
            grid = cdp_eval("JSON.stringify(window.__grid || null)")
        except Exception:
            grid = None
        best = None
        if grid:
            try:
                g = json.loads(grid)
                best = self._pick(g)
            except Exception:
                best = None
        if best is None:
            best = ["left", "down", "right", "up"][self.i % 4]
        self.i += 1
        key = {"left": "KEY left", "down": "KEY down",
               "right": "KEY right", "up": "KEY up"}[best]
        return "(scripted) 2048 move %s" % best, ("key", best)

    @staticmethod
    def _pick(g):
        """Greedy: prefer keeping the largest tile in a corner."""
        empty = sum(1 for row in g for v in row if not v)
        best_move, best_score = None, -1
        for m in ("left", "down", "right", "up"):
            ng = _slide(g, m)
            if ng is None:
                continue
            score = sum(v for row in ng for v in row)
            score += empty * 2
            corner = max(ng[0][0], ng[-1][-1], ng[0][-1], ng[-1][0])
            score += corner * 3
            if score > best_score:
                best_score, best_move = score, m
        return best_move




def cdp_eval(expr):
    return _page_state(expr)
