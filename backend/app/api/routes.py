"""
FastAPI routes for project and segment management.
"""
import os
import uuid
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
import logging

from app.models import ProjectCreate, ProjectResponse, SegmentResponse
from app.core.processing_pipeline import ProcessingPipeline
from app.core.kml_exporter import KMLExporter

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage (replace with database in production)
projects_db = {}
segments_db = {}
pipeline_instances = {}  # Store pipeline instances for cancellation

# Thread pool for running async tasks in background
executor = ThreadPoolExecutor(max_workers=4)


@router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """
    Create a new search segment project.

    Args:
        project: Project creation data

    Returns:
        Created project with ID
    """
    try:
        # Generate project ID
        project_id = str(uuid.uuid4())

        # Store project
        now = datetime.now()
        project_data = {
            'id': project_id,
            'name': project.name,
            'status': 'created',
            'search_polygon': project.search_polygon,
            'drone_agl_altitude': project.drone_agl_altitude,
            'preferred_segment_size_acres': project.preferred_segment_size_acres,
            'max_vlos_m': project.max_vlos_m,
            'access_types': project.access_types,
            'access_deviation_m': project.access_deviation_m,
            'grid_spacing_m': project.grid_spacing_m,
            'segment_count': 0,
            'total_area_acres': None,
            'created_at': now,
            'updated_at': now,
            'error_message': None
        }

        projects_db[project_id] = project_data

        logger.info(f"Created project {project_id}: {project.name}")

        return ProjectResponse(**project_data)

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/upload-dem")
async def upload_dem(
    project_id: str,
    dem_file: UploadFile = File(...),
    vegetation_file: UploadFile = File(None)
):
    """
    Upload DEM and optional vegetation files for a project.

    Args:
        project_id: Project UUID
        dem_file: DEM GeoTIFF file
        vegetation_file: Optional vegetation height GeoTIFF

    Returns:
        Success message
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Create upload directory
        upload_dir = f"/app/data/projects/{project_id}"
        os.makedirs(upload_dir, exist_ok=True)

        # Save DEM file
        dem_path = os.path.join(upload_dir, "dem.tif")
        with open(dem_path, "wb") as f:
            content = await dem_file.read()
            f.write(content)

        projects_db[project_id]['dem_path'] = dem_path

        # Save vegetation file if provided
        if vegetation_file:
            veg_path = os.path.join(upload_dir, "vegetation.tif")
            with open(veg_path, "wb") as f:
                content = await vegetation_file.read()
                f.write(content)
            projects_db[project_id]['vegetation_path'] = veg_path

        logger.info(f"Uploaded DEM for project {project_id}")

        return {"message": "Files uploaded successfully"}

    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/calculate")
async def calculate_segments(project_id: str):
    """
    Calculate search segments for a project.

    Args:
        project_id: Project UUID

    Returns:
        Processing status message
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]

    if project['status'] == 'processing':
        raise HTTPException(status_code=400, detail="Project is already being processed")

    # Initialize progress tracking BEFORE setting status to 'processing'
    # This prevents race condition where frontend polls before progress is initialized
    projects_db[project_id]['progress'] = 0
    projects_db[project_id]['current_step'] = 'Starting...'
    projects_db[project_id]['updated_at'] = datetime.now()

    # Update status
    projects_db[project_id]['status'] = 'processing'

    # Start processing in background using thread pool
    # This ensures asyncio.run() has its own event loop context
    executor.submit(process_project, project_id)

    return {
        "message": "Processing started",
        "project_id": project_id,
        "status": "processing"
    }


def process_project(project_id: str):
    """
    Background task to process a project.

    This is a synchronous function that creates its own event loop to run
    the async pipeline. This ensures the HTTP response returns immediately
    while processing continues in the background.

    Args:
        project_id: Project UUID
    """
    async def _process():
        """Inner async function that does the actual processing."""
        try:
            project = projects_db[project_id]

            # Build config for pipeline
            config = {
                'project_id': project_id,
                'search_polygon': project['search_polygon'],
                'drone_agl_altitude': project['drone_agl_altitude'],
                'preferred_segment_size_acres': project['preferred_segment_size_acres'],
                'max_vlos_m': project['max_vlos_m'],
                'access_types': project['access_types'],
                'access_deviation_m': project['access_deviation_m'],
                'grid_spacing_m': project['grid_spacing_m'],
                'dem_path': project.get('dem_path'),
                'vegetation_path': project.get('vegetation_path'),
                'roads_path': project.get('roads_path'),
                'trails_path': project.get('trails_path'),
                'output_dir': f"/app/data/projects/{project_id}/output"
            }

            # Create progress callback
            def update_progress(step: str, progress: int):
                projects_db[project_id]['current_step'] = step
                projects_db[project_id]['progress'] = progress
                projects_db[project_id]['updated_at'] = datetime.now()
                logger.info(f"Project {project_id} progress: {progress}% - {step}")

            # Execute pipeline
            pipeline = ProcessingPipeline(config, progress_callback=update_progress)

            # Store pipeline instance for cancellation
            pipeline_instances[project_id] = pipeline

            results = await pipeline.execute()

            # Remove pipeline instance after completion
            if project_id in pipeline_instances:
                del pipeline_instances[project_id]

            if results['success']:
                # Store segments
                segments_db[project_id] = results['segments']

                # Update project
                projects_db[project_id]['status'] = 'completed'
                projects_db[project_id]['segment_count'] = len(results['segments'])
                projects_db[project_id]['progress'] = 100
                projects_db[project_id]['current_step'] = 'Complete'

                logger.info(f"Project {project_id} processing completed")

            else:
                # Check if it was cancelled
                error_msg = results.get('error', '')
                if 'Cancelled' in error_msg:
                    projects_db[project_id]['status'] = 'cancelled'
                else:
                    projects_db[project_id]['status'] = 'failed'
                projects_db[project_id]['error_message'] = error_msg
                logger.error(f"Project {project_id} processing failed: {error_msg}")

        except Exception as e:
            # Remove pipeline instance on error
            if project_id in pipeline_instances:
                del pipeline_instances[project_id]

            projects_db[project_id]['status'] = 'failed'
            projects_db[project_id]['error_message'] = str(e)
            logger.error(f"Error processing project {project_id}: {e}", exc_info=True)

    # Run the async function in a new event loop
    asyncio.run(_process())


@router.get("/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """
    Get processing status for a project.

    Args:
        project_id: Project UUID

    Returns:
        Current processing status, progress, and step
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]

    status_response = {
        'project_id': project_id,
        'status': project['status'],
        'progress': project.get('progress', 0),
        'current_step': project.get('current_step', ''),
        'segment_count': project.get('segment_count', 0),
        'error_message': project.get('error_message')
    }

    logger.debug(f"Status request for {project_id}: {project['status']}, progress={status_response['progress']}%")

    return status_response


@router.post("/projects/{project_id}/cancel")
async def cancel_project(project_id: str):
    """
    Cancel processing for a project.

    Args:
        project_id: Project UUID

    Returns:
        Cancellation confirmation
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    project = projects_db[project_id]

    # If already completed, cancelled, or failed, just return success
    if project['status'] in ['completed', 'cancelled', 'failed']:
        logger.info(f"Cancel requested for project {project_id} but it's already {project['status']}")
        return {
            'message': f'Project already {project["status"]}',
            'project_id': project_id,
            'status': project['status']
        }

    # If not processing, we can't cancel
    if project['status'] != 'processing':
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel project with status: {project['status']}"
        )

    # Cancel the pipeline if it exists
    if project_id in pipeline_instances:
        pipeline = pipeline_instances[project_id]
        pipeline.cancel()
        logger.info(f"Cancellation requested for project {project_id}")

        return {
            'message': 'Cancellation requested',
            'project_id': project_id
        }
    else:
        # Pipeline might not be in dict yet if processing just started
        # or might have just finished. Mark as cancelled anyway.
        logger.warning(f"Cancel requested for project {project_id} but no active pipeline found")
        projects_db[project_id]['status'] = 'cancelled'
        projects_db[project_id]['current_step'] = 'Cancelled'
        return {
            'message': 'Cancellation marked (pipeline already completed or not started)',
            'project_id': project_id
        }


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    Get project details.

    Args:
        project_id: Project UUID

    Returns:
        Project details
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(**projects_db[project_id])


@router.get("/projects/{project_id}/segments")
async def get_segments(project_id: str):
    """
    Get segments for a project as GeoJSON.

    Args:
        project_id: Project UUID

    Returns:
        GeoJSON FeatureCollection of segments
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_id not in segments_db:
        raise HTTPException(status_code=404, detail="Segments not yet generated")

    segments = segments_db[project_id]

    # Convert to GeoJSON FeatureCollection
    features = []
    for segment in segments:
        feature = {
            'type': 'Feature',
            'properties': {
                'sequence': segment['sequence'],
                'area_acres': segment['area_acres'],
                'access_type': segment['access_type'],
                'launch_point': segment['launch_point']
            },
            'geometry': segment['polygon']
        }
        features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    return geojson


@router.get("/projects/{project_id}/export-kml")
async def export_kml(project_id: str):
    """
    Export segments to KML file.

    Args:
        project_id: Project UUID

    Returns:
        KML file download
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_id not in segments_db:
        raise HTTPException(status_code=404, detail="Segments not yet generated")

    try:
        project = projects_db[project_id]
        segments = segments_db[project_id]

        # Export to KML
        exporter = KMLExporter()

        output_dir = f"/app/exports/{project_id}"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{project['name']}.kml")

        exporter.export_project(
            project['name'],
            project['search_polygon'],
            segments,
            output_path
        )

        return FileResponse(
            output_path,
            media_type='application/vnd.google-earth.kml+xml',
            filename=f"{project['name']}.kml"
        )

    except Exception as e:
        logger.error(f"Error exporting KML: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def list_projects():
    """
    List all projects.

    Returns:
        List of projects
    """
    return {
        'projects': list(projects_db.values()),
        'total': len(projects_db)
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project.

    Args:
        project_id: Project UUID

    Returns:
        Success message
    """
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="Project not found")

    del projects_db[project_id]

    if project_id in segments_db:
        del segments_db[project_id]

    logger.info(f"Deleted project {project_id}")

    return {"message": "Project deleted successfully"}
