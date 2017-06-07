"""Tile class."""

from shapely.geometry import box
from affine import Affine

from . import _conf, _funcs


class Tile(object):
    """
    A Tile is a square somewhere on Earth.

    Each Tile can be identified with the zoom, row, column index in a
    TilePyramid.

    Some tile functions can accept a tile buffer in pixels (pixelbuffer). A
    pixelbuffer value of e.g. 1 will extend the tile boundaries by 1 pixel.
    """

    def __init__(self, tile_pyramid, zoom, row, col):
        """Initialize Tile."""
        self.tile_pyramid = tile_pyramid
        self.tp = tile_pyramid
        self.crs = tile_pyramid.crs
        self.zoom = zoom
        self.row = row
        self.col = col
        try:
            assert self.is_valid()
        except AssertionError:
            raise ValueError("invalid tile index given: %s %s %s" % (
                zoom, row, col))
        self.index = (zoom, row, col)
        self.id = (zoom, row, col)
        self.pixel_x_size = self.tile_pyramid.pixel_x_size(self.zoom)
        self.pixel_y_size = self.tile_pyramid.pixel_y_size(self.zoom)
        self.left = float(round(
            self.tile_pyramid.left+((self.col)*self.x_size),
            _conf.ROUND)
        )
        self.top = float(round(
            self.tile_pyramid.top-((self.row)*self.y_size),
            _conf.ROUND)
        )
        self.right = self.left + self.x_size
        self.bottom = self.top - self.y_size
        self.srid = tile_pyramid.srid

    @property
    def width(self):
        """Calculate Tile width in pixels."""
        return self.tile_pyramid.tile_width(self.zoom)

    @property
    def height(self):
        """Calculate Tile height in pixels."""
        return self.tile_pyramid.tile_height(self.zoom)

    @property
    def x_size(self):
        """Width of tile in SRID units at zoom level."""
        return self.tile_pyramid.tile_x_size(self.zoom)

    @property
    def y_size(self):
        """Height of tile in SRID units at zoom level."""
        return self.tile_pyramid.tile_y_size(self.zoom)

    def bounds(self, pixelbuffer=0):
        """
        Return Tile boundaries.

        - pixelbuffer: tile buffer in pixels
        """
        left = self.left
        bottom = self.top - self.y_size
        right = self.left + self.x_size
        top = self.top
        if pixelbuffer > 0:
            assert isinstance(pixelbuffer, int)
            offset = self.pixel_x_size * float(pixelbuffer)
            left -= offset
            bottom -= offset
            right += offset
            top += offset
        if top > self.tile_pyramid.top:
            top = self.tile_pyramid.top
        if bottom < self.tile_pyramid.bottom:
            bottom = self.tile_pyramid.bottom
        return (left, bottom, right, top)

    def bbox(self, pixelbuffer=0):
        """
        Return Tile bounding box.

        - pixelbuffer: tile buffer in pixels
        """
        return box(*self.bounds(pixelbuffer=pixelbuffer))

    def affine(self, pixelbuffer=0):
        """
        Return an Affine object of tile.

        - pixelbuffer: tile buffer in pixels
        """
        left = self.bounds(pixelbuffer)[0]
        top = self.bounds(pixelbuffer=pixelbuffer)[3]
        return Affine(self.pixel_x_size, 0, left, 0, -self.pixel_y_size, top)

    def shape(self, pixelbuffer=0):
        """
        Return a tuple of tile height and width.

        - pixelbuffer: tile buffer in pixels
        """
        height = self.height + 2 * pixelbuffer
        width = self.width + 2 * pixelbuffer
        if pixelbuffer:
            matrix_height = self.tile_pyramid.matrix_height(self.zoom)
            if matrix_height == 1:
                height = self.height
            elif self.row in [0, matrix_height-1]:
                height = self.height + pixelbuffer
        return (height, width)

    def is_valid(self):
        """Return True if tile is available in tile pyramid."""
        try:
            assert isinstance(self.zoom, int)
            assert self.zoom >= 0
            assert isinstance(self.row, int)
            assert self.row >= 0
            assert isinstance(self.col, int)
            assert self.col >= 0
            assert self.col < self.tile_pyramid.matrix_width(self.zoom)
            assert self.row < self.tile_pyramid.matrix_height(self.zoom)
        except AssertionError:
            return False
        else:
            return True

    def get_parent(self):
        """Return tile from previous zoom level."""
        if self.zoom == 0:
            return None
        else:
            return self.tile_pyramid.tile(
                self.zoom-1, int(self.row/2), int(self.col/2))

    def get_children(self):
        """Return tiles from next zoom level."""
        matrix_offsets = [
            (0, 0),  # top left
            (0, 1),  # top right
            (1, 1),  # bottom right
            (1, 0),  # bottom left
        ]
        new_zoom = self.zoom + 1
        children = []
        for row_offset, col_offset in matrix_offsets:
            new_row = self.row * 2 + row_offset
            new_col = self.col * 2 + col_offset
            if (
                new_row >= self.tp.matrix_height(new_zoom)
                ) or (
                new_col >= self.tp.matrix_width(new_zoom)
            ):
                continue
            children.append(
                self.tile_pyramid.tile(new_zoom, new_row, new_col)
            )
        return children

    def get_neighbors(self, connectedness=8):
        """
        Return tile neighbors.

        Tile neighbors are unique, i.e. in some edge cases, where both the left
        and right neighbor wrapped around the antimeridian is the same. Also,
        neighbors ouside the northern and southern TilePyramid boundaries are
        excluded, because they are invalid.

        -------------
        | 8 | 1 | 5 |
        -------------
        | 4 | x | 2 |
        -------------
        | 7 | 3 | 6 |
        -------------

        - connectedness: [4 or 8] return four direct neighbors or all eight.
        """
        if connectedness not in [4, 8]:
            raise ValueError("only connectedness values 8 or 4 are allowed")

        unique_neighbors = {}
        # 4-connected neighborsfor pyramid
        matrix_offsets = [
            (-1, 0),  # 1: above
            (0, 1),   # 2: right
            (1, 0),   # 3: below
            (0, -1)   # 4: left
        ]
        if connectedness == 8:
            matrix_offsets.extend([
                (-1, 1),  # 5: above right
                (1, 1),   # 6: below right
                (1, -1),  # 7: below left
                (-1, -1)  # 8: above left
            ])

        for row_offset, col_offset in matrix_offsets:
            new_row = self.row + row_offset
            new_col = self.col + col_offset
            # omit if row is outside of tile matrix
            if new_row < 0 or new_row >= self.tp.matrix_height(self.zoom):
                continue
            # wrap around antimeridian if new column is outside of tile matrix
            if new_col < 0:
                if not self.tp.is_global:
                    continue
                new_col = self.tp.matrix_width(self.zoom) + new_col
            elif new_col >= self.tp.matrix_width(self.zoom):
                if not self.tp.is_global:
                    continue
                new_col -= self.tp.matrix_width(self.zoom)
            # omit if new tile is current tile
            if new_row == self.row and new_col == self.col:
                continue
            # create new tile
            unique_neighbors[(new_row, new_col)] = self.tp.tile(
                self.zoom, new_row, new_col
            )

        return unique_neighbors.values()

    def intersecting(self, tilepyramid):
        """
        Return all Tiles from intersecting TilePyramid.

        This helps translating between TilePyramids with different metatiling
        settings.

        - tilepyramid: a TilePyramid object
        """
        return _funcs._tile_intersecting_tilepyramid(self, tilepyramid)