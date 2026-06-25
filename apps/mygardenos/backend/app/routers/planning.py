from fastapi import APIRouter

from app.routers.mowing_workflow import router as mowing_workflow_router
from app.routers.property_maps import router as property_maps_router
from app.routers.robot_runtime import router as robot_runtime_router


router = APIRouter()
router.include_router(property_maps_router)
router.include_router(mowing_workflow_router)
router.include_router(robot_runtime_router)
