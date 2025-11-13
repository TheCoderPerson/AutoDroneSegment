"""
DEM (Digital Elevation Model) Processor.

Handles:
- DEM clipping to search area
- CRS reprojection to UTM
- Vegetation height integration
- Cell indexing for visibility tracking
"""
import os
import tempfile
from typing import Tuple, Optional, Dict
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import shape, box, mapping
import logging

logger = logging.getLogger(__name__)


class DEMProcessor:
    """Process DEM rasters for viewshed analysis."""

    def __init__(self, dem_path: str, vegetation_path: Optional[str] = None):
        """
        Initialize DEM processor.

        Args:
            dem_path: Path to DEM GeoTIFF file
            vegetation_path: Optional path to vegetation height GeoTIFF
        """
        self.dem_path = dem_path
        self.vegetation_path = vegetation_path
        self.processed_dem_path: Optional[str] = None
        self.cell_index: Dict[int, Tuple[float, float]] = {}
        self.transform = None
        self.width = None
        self.height = None
        self.epsg = None

    def process(
        self,
        polygon_geojson: dict,
        target_epsg: int,
        max_vlos_m: float,
        output_dir: str
    ) -> str:
        """
        Process DEM: clip, reproject, and optionally add vegetation.

        Args:
            polygon_geojson: Search polygon in target CRS
            target_epsg: Target EPSG code (UTM)
            max_vlos_m: Maximum VLOS distance for buffer
            output_dir: Directory to save processed DEM

        Returns:
            Path to processed DEM file
        """
        logger.info("Starting DEM processing...")

        # Create buffer around polygon
        geom = shape(polygon_geojson)
        buffered_geom = geom.buffer(max_vlos_m)

        # Check DEM CRS and transform polygon if needed
        import rasterio
        with rasterio.open(self.dem_path) as src:
            dem_crs = src.crs
            logger.info(f"DEM CRS: {dem_crs}, Target CRS: EPSG:{target_epsg}")

            # If DEM is in a different CRS than our polygon, transform polygon to DEM CRS for clipping
            if dem_crs.to_epsg() != target_epsg:
                logger.info(f"Transforming polygon from EPSG:{target_epsg} to {dem_crs} for clipping")
                from app.core.crs_manager import CRSManager
                buffered_geom_dict = mapping(buffered_geom)
                transformed_geom_dict = CRSManager.transform_geometry(
                    buffered_geom_dict,
                    from_epsg=target_epsg,
                    to_epsg=dem_crs.to_epsg()
                )
                buffered_geom = shape(transformed_geom_dict)

        # Step 1: Clip DEM to buffered area (now in DEM's CRS)
        clipped_dem_path = self._clip_dem(buffered_geom, output_dir)

        # Step 2: Reproject to target CRS if needed
        reprojected_dem_path = self._reproject_dem(clipped_dem_path, target_epsg, output_dir)

        # Step 3: Add vegetation if available
        if self.vegetation_path and os.path.exists(self.vegetation_path):
            final_dem_path = self._add_vegetation(
                reprojected_dem_path,
                buffered_geom,
                target_epsg,
                output_dir
            )
        else:
            final_dem_path = reprojected_dem_path

        # Step 4: Build cell index
        self._build_cell_index(final_dem_path)

        self.processed_dem_path = final_dem_path
        logger.info(f"DEM processing complete: {final_dem_path}")

        return final_dem_path

    def _clip_dem(self, geom, output_dir: str) -> str:
        """Clip DEM to geometry bounds."""
        logger.info("Clipping DEM to search area...")

        with rasterio.open(self.dem_path) as src:
            # Log DEM information
            logger.info(f"DEM CRS: {src.crs}")
            logger.info(f"DEM bounds: {src.bounds}")
            logger.info(f"DEM shape: {src.shape}")

            # Get geometry bounds for logging
            from shapely.geometry import shape as shapely_shape
            geom_shape = shapely_shape(geom) if isinstance(geom, dict) else geom
            logger.info(f"Polygon bounds: {geom_shape.bounds}")

            try:
                # Clip the raster
                out_image, out_transform = mask(src, [geom], crop=True)

                # Check if we got any data
                if out_image.size == 0:
                    raise ValueError(
                        "Clipping resulted in empty raster. "
                        "This usually means the polygon and DEM don't overlap. "
                        f"DEM CRS: {src.crs}, DEM bounds: {src.bounds}, "
                        f"Polygon bounds: {geom_shape.bounds}"
                    )

                out_meta = src.meta.copy()

                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })

                # Save clipped DEM
                output_path = os.path.join(output_dir, "dem_clipped.tif")
                with rasterio.open(output_path, "w", **out_meta) as dest:
                    dest.write(out_image)

                logger.info(f"Clipped DEM saved: {out_image.shape}")

            except ValueError as e:
                if "Input shapes do not overlap" in str(e):
                    logger.error(
                        f"DEM and polygon do not overlap!\n"
                        f"DEM CRS: {src.crs}\n"
                        f"DEM bounds: {src.bounds}\n"
                        f"Polygon bounds: {geom_shape.bounds}\n"
                        f"Suggestion: Ensure your DEM covers the search area and both are in compatible coordinate systems."
                    )
                raise

        return output_path

    def _reproject_dem(self, dem_path: str, target_epsg: int, output_dir: str) -> str:
        """Reproject DEM to target CRS."""
        logger.info(f"Reprojecting DEM to EPSG:{target_epsg}...")

        with rasterio.open(dem_path) as src:
            src_crs = src.crs

            # Check if reprojection is needed
            if src_crs.to_epsg() == target_epsg:
                logger.info("DEM already in target CRS")
                return dem_path

            # Calculate transform
            transform, width, height = calculate_default_transform(
                src_crs,
                f"EPSG:{target_epsg}",
                src.width,
                src.height,
                *src.bounds
            )

            # Update metadata
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': f"EPSG:{target_epsg}",
                'transform': transform,
                'width': width,
                'height': height
            })

            # Perform reprojection
            output_path = os.path.join(output_dir, "dem_reprojected.tif")
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=f"EPSG:{target_epsg}",
                        resampling=Resampling.bilinear
                    )

        return output_path

    def _add_vegetation(
        self,
        dem_path: str,
        geom,
        target_epsg: int,
        output_dir: str
    ) -> str:
        """Add vegetation height to DEM."""
        logger.info("Adding vegetation height to DEM...")

        # Process vegetation raster similar to DEM
        with rasterio.open(self.vegetation_path) as veg_src:
            # Clip
            veg_image, veg_transform = mask(veg_src, [geom], crop=True)

            # Reproject if needed
            if veg_src.crs.to_epsg() != target_epsg:
                # Similar reprojection logic
                pass

        # Combine DEM + vegetation
        with rasterio.open(dem_path) as dem_src:
            dem_data = dem_src.read(1)

            # Resample vegetation to match DEM if needed
            # For simplicity, assuming they match
            veg_data = veg_image[0]

            # Ensure same shape
            if dem_data.shape != veg_data.shape:
                # Resize vegetation data to match DEM
                from scipy.ndimage import zoom
                zoom_factors = (
                    dem_data.shape[0] / veg_data.shape[0],
                    dem_data.shape[1] / veg_data.shape[1]
                )
                veg_data = zoom(veg_data, zoom_factors, order=1)

            # Combine: effective_surface = DEM + vegetation_height
            combined = dem_data + veg_data

            # Save combined DEM
            output_path = os.path.join(output_dir, "dem_with_vegetation.tif")
            meta = dem_src.meta.copy()

            with rasterio.open(output_path, 'w', **meta) as dst:
                dst.write(combined, 1)

        return output_path

    def _build_cell_index(self, dem_path: str):
        """Build index of cell ID to centroid coordinates."""
        logger.info("Building cell index...")

        with rasterio.open(dem_path) as src:
            self.transform = src.transform
            self.width = src.width
            self.height = src.height
            self.epsg = src.crs.to_epsg()

            cell_id = 0
            for row in range(self.height):
                for col in range(self.width):
                    # Get cell centroid
                    x, y = rasterio.transform.xy(self.transform, row, col, offset='center')
                    self.cell_index[cell_id] = (x, y)
                    cell_id += 1

        logger.info(f"Built index for {len(self.cell_index)} cells")

    def get_cell_coordinates(self, cell_ids: list) -> list:
        """
        Get coordinates for a list of cell IDs.

        Args:
            cell_ids: List of cell IDs

        Returns:
            List of (x, y) tuples
        """
        return [self.cell_index.get(cid) for cid in cell_ids if cid in self.cell_index]

    def get_cell_area(self) -> float:
        """
        Get area of a single cell in square meters.

        Returns:
            Cell area in m²
        """
        if self.transform is None:
            return 0.0

        # Cell dimensions from transform
        cell_width = abs(self.transform[0])
        cell_height = abs(self.transform[4])

        return cell_width * cell_height
