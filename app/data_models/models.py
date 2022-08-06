from pydantic import BaseModel, conlist, NonNegativeInt
from typing import Union, Literal

# type aliases for the model
AlgaeType = Literal["Sample", "Sighting", "Undefined"]
AlgaeSize = Literal[
    "Fist",
    "Shoe Box",
    "Coffee Table",
    "Car",
    "Bus",
    "Playground",
    "Sports Field",
    "Other",
]
AlgaeColor = Literal["Other", "Red", "Pink", "Grey", "Green", "Orange", "Yellow"]


class PhotoEntry(BaseModel):
    uri: str  # name of the photo file in Blob Storage Container
    width: NonNegativeInt
    height: NonNegativeInt
    size: Union[NonNegativeInt, None]


class Record(BaseModel):
    id: NonNegativeInt
    type: AlgaeType
    name: Union[str, None]
    organization: Union[str, None]
    date: str
    longitude: float
    latitude: float
    size: AlgaeSize
    color: AlgaeColor
    tubeId: Union[str, None]
    locationDescription: Union[str, None]
    notes: Union[str, None]
    photos: Union[conlist(PhotoEntry, max_items=4), None]
