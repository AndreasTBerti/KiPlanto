from fastapi import APIRouter
from model.crop_model import crop_prev
from schemas.api_schema import PrevisionInput, PrevisionOutput

router = APIRouter(prefix="/ai")

@router.post("/prevision", response_model=PrevisionOutput)
def get_prev(data: PrevisionInput):
    pass