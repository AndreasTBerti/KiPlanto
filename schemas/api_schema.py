from pydantic import BaseModel

class PrevisionInput(BaseModel):
    city: str
    n_ratio: float
    p_ratio: float
    k_ratio: float
    ph: float


class PrevisionOutput(BaseModel):
    crop_recomendation: str