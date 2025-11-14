"""
KML/KMZ Export functionality.

Exports segments, launch points, and search boundaries to KML format
for use in field operations.
"""
import simplekml
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class KMLExporter:
    """Export segments to KML/KMZ format."""

    def __init__(self):
        """Initialize KML exporter."""
        self.kml = None

    def export_project(
        self,
        project_name: str,
        search_polygon: dict,
        segments: List[Dict],
        output_path: str,
        include_stats: bool = True
    ) -> str:
        """
        Export project to KML file.

        Args:
            project_name: Name of the project
            search_polygon: Search boundary polygon (GeoJSON in WGS84)
            segments: List of segment dictionaries (in WGS84)
            output_path: Path to save KML file
            include_stats: Include statistics folder

        Returns:
            Path to generated KML file
        """
        logger.info(f"Exporting project '{project_name}' to KML...")

        self.kml = simplekml.Kml()
        self.kml.document.name = project_name

        # Add search boundary
        self._add_search_boundary(search_polygon)

        # Add segments
        self._add_segments(segments)

        # Add launch points
        self._add_launch_points(segments)

        # Add statistics
        if include_stats:
            self._add_statistics(segments, project_name)

        # Save KML
        self.kml.save(output_path)

        logger.info(f"KML saved to {output_path}")

        return output_path

    def _add_search_boundary(self, polygon_geojson: dict):
        """Add search boundary to KML."""
        folder = self.kml.newfolder(name="Search Boundary")

        # Extract coordinates from GeoJSON
        coords = self._extract_coordinates(polygon_geojson)

        if coords:
            poly = folder.newpolygon(name="Search Area")
            poly.outerboundaryis = coords

            # Style
            poly.style.linestyle.color = simplekml.Color.red
            poly.style.linestyle.width = 3
            poly.style.polystyle.color = simplekml.Color.changealphaint(50, simplekml.Color.red)

    def _add_segments(self, segments: List[Dict]):
        """Add segment polygons to KML."""
        folder = self.kml.newfolder(name="Search Segments")

        # Color palette for segments
        colors = [
            simplekml.Color.blue,
            simplekml.Color.green,
            simplekml.Color.yellow,
            simplekml.Color.orange,
            simplekml.Color.purple,
            simplekml.Color.cyan,
            simplekml.Color.pink,
        ]

        for segment in segments:
            seq = segment['sequence']
            polygon_geom = segment['polygon']

            # Description
            desc = self._build_segment_description(segment)

            # Style - cycle through colors
            color = colors[(seq - 1) % len(colors)]

            # Extract all polygon coordinates (handles both Polygon and MultiPolygon)
            all_coords = self._extract_all_coordinates(polygon_geom)

            if len(all_coords) == 1:
                # Single polygon - create simple polygon
                poly = folder.newpolygon(name=f"Segment {seq}")
                poly.outerboundaryis = all_coords[0]
                poly.description = desc
                poly.style.linestyle.color = simplekml.Color.black
                poly.style.linestyle.width = 2
                poly.style.polystyle.color = simplekml.Color.changealphaint(100, color)
            else:
                # MultiPolygon - create a single placemark with MultiGeometry
                multi = folder.newmultigeometry(name=f"Segment {seq}")
                multi.description = desc

                for coords in all_coords:
                    if coords:
                        poly = multi.newpolygon()
                        poly.outerboundaryis = coords
                        poly.style.linestyle.color = simplekml.Color.black
                        poly.style.linestyle.width = 2
                        poly.style.polystyle.color = simplekml.Color.changealphaint(100, color)

    def _add_launch_points(self, segments: List[Dict]):
        """Add launch points to KML."""
        folder = self.kml.newfolder(name="Launch Points")

        for segment in segments:
            seq = segment['sequence']
            launch_point = segment['launch_point']

            # Extract coordinates
            if 'coordinates' in launch_point:
                lon, lat = launch_point['coordinates']
            else:
                continue

            # Create placemark
            pnt = folder.newpoint(name=f"Launch Point {seq}")
            pnt.coords = [(lon, lat)]

            # Description
            desc = f"""
            <b>Segment {seq} Launch Point</b><br/>
            Coordinates: {lat:.6f}, {lon:.6f}<br/>
            Area: {segment.get('area_acres', 0):.2f} acres<br/>
            Access: {segment.get('access_type', 'unknown')}
            """
            pnt.description = desc

            # Style
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/heliport.png'
            pnt.style.iconstyle.scale = 1.2

    def _add_statistics(self, segments: List[Dict], project_name: str):
        """Add statistics folder to KML."""
        folder = self.kml.newfolder(name="Statistics")

        # Calculate statistics
        total_segments = len(segments)
        total_area_acres = sum(seg.get('area_acres', 0) for seg in segments)

        areas = [seg.get('area_acres', 0) for seg in segments]
        min_area = min(areas) if areas else 0
        max_area = max(areas) if areas else 0
        avg_area = total_area_acres / total_segments if total_segments > 0 else 0

        # Create a point for statistics (at first launch point)
        if segments and segments[0]['launch_point'].get('coordinates'):
            lon, lat = segments[0]['launch_point']['coordinates']

            stats_point = folder.newpoint(name="Project Statistics")
            stats_point.coords = [(lon, lat)]

            desc = f"""
            <h2>{project_name} - Statistics</h2>
            <table border="1">
                <tr><td><b>Total Segments</b></td><td>{total_segments}</td></tr>
                <tr><td><b>Total Area</b></td><td>{total_area_acres:.2f} acres</td></tr>
                <tr><td><b>Average Segment Size</b></td><td>{avg_area:.2f} acres</td></tr>
                <tr><td><b>Min Segment Size</b></td><td>{min_area:.2f} acres</td></tr>
                <tr><td><b>Max Segment Size</b></td><td>{max_area:.2f} acres</td></tr>
            </table>
            """
            stats_point.description = desc

            # Style
            stats_point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/info.png'

    def _extract_all_coordinates(self, geojson_geom: dict) -> list:
        """
        Extract all polygon coordinates from GeoJSON geometry.

        Handles both Polygon and MultiPolygon, returning a list of coordinate lists.

        Args:
            geojson_geom: GeoJSON geometry

        Returns:
            List of coordinate lists, one for each polygon
        """
        geom_type = geojson_geom.get('type')

        if geom_type == 'Polygon':
            coords = geojson_geom['coordinates'][0]  # Outer ring
            return [[(lon, lat) for lon, lat in coords]]

        elif geom_type == 'MultiPolygon':
            # Extract all polygons
            all_polys = geojson_geom['coordinates']
            result = []
            for poly in all_polys:
                coords = poly[0]  # Outer ring of this polygon
                result.append([(lon, lat) for lon, lat in coords])
            return result

        return []

    def _extract_coordinates(self, geojson_geom: dict) -> list:
        """
        Extract coordinates from GeoJSON geometry.

        Args:
            geojson_geom: GeoJSON geometry

        Returns:
            List of (lon, lat) tuples for a single polygon, or list of lists for MultiPolygon
        """
        geom_type = geojson_geom.get('type')

        if geom_type == 'Polygon':
            coords = geojson_geom['coordinates'][0]  # Outer ring
            return [(lon, lat) for lon, lat in coords]

        elif geom_type == 'MultiPolygon':
            # Use the largest polygon from MultiPolygon
            all_polys = geojson_geom['coordinates']
            if not all_polys:
                return []

            # Find polygon with most vertices (proxy for largest area)
            largest_poly = max(all_polys, key=lambda p: len(p[0]))
            coords = largest_poly[0]  # Outer ring of largest polygon

            logger.warning(
                f"MultiPolygon with {len(all_polys)} parts detected in KML export. "
                f"Using largest polygon only."
            )

            return [(lon, lat) for lon, lat in coords]

        return []

    def _build_segment_description(self, segment: Dict) -> str:
        """Build HTML description for segment."""
        desc = f"""
        <b>Segment {segment['sequence']}</b><br/>
        Area: {segment.get('area_acres', 0):.2f} acres ({segment.get('area_m2', 0):.0f} m²)<br/>
        Access Type: {segment.get('access_type', 'unknown')}<br/>
        Launch Point: {segment['launch_point'].get('coordinates', ['?', '?'])[1]:.6f},
                      {segment['launch_point'].get('coordinates', ['?', '?'])[0]:.6f}
        """
        return desc
