#!/usr/bin/env python
"""TilePyramid creation."""

from tilematrix import TilePyramid


def test_init():
    """Initialize TilePyramids."""
    for tptype in ["geodetic", "mercator"]:
        assert TilePyramid(tptype)
    try:
        TilePyramid("invalid")
        raise Exception()
    except ValueError:
        pass


def test_metatiling():
    """Metatiling setting."""
    for metatiling in [1, 2, 4, 8, 16]:
        assert TilePyramid("geodetic", metatiling=metatiling)
    try:
        TilePyramid("geodetic", metatiling=5)
        raise Exception()
    except ValueError:
        pass


def test_tile_size():
    """Tile sizes."""
    for tile_size in [128, 256, 512, 1024]:
        tp = TilePyramid("geodetic", tile_size=tile_size)
        assert tp.tile_size == tile_size


def test_intersect():
    """Get intersecting Tiles."""
    tp = TilePyramid("geodetic")
    tp_meta = TilePyramid("geodetic", metatiling=2)
    metatile = tp_meta.tile(5, 1, 1)
    control = {(5, 2, 2), (5, 2, 3), (5, 3, 3), (5, 3, 2)}
    test_tiles = {tile.id for tile in tp.intersecting(metatile)}
    assert control == test_tiles
