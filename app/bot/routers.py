from aiogram import Router

from .handlers_common import router as common_router
from .handlers_start import router as start_router
from .handlers_measurements import router as meas_router
from .handlers_history import router as hist_router
from .handlers_reminders import router as rem_router

def setup_routers() -> Router:
    root = Router()
    root.include_router(common_router) 
    root.include_router(start_router)
    root.include_router(meas_router)
    root.include_router(hist_router)
    root.include_router(rem_router)
    return root