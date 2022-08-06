from io import BytesIO
from fastapi import Depends, FastAPI, HTTPException, Response, Request
from typing import List
from PIL import Image
import sqlite3
import json
import logging
import datetime

from logging.config import dictConfig
from my_logger.config import LogConfig
from data_models.models import Record, PhotoEntry
from AppSettings import App


_create_records_table = """
    CREATE TABLE IF NOT EXISTS records
        (id INTEGER PRIMARY KEY,
        type TEST NOT NULL,
        name TEXT, organization TEXT,
        date TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        size TEXT NOT NULL,
        color TEXT NOT NULL,
        tubeId TEXT,
        locationDescription TEXT,
        notes TEXT,
        photos TEXT NOT NULL);
"""

_create_photo_blob_table = """
    CREATE TABLE IF NOT EXISTS photos
        (uri TEXT PRIMARY KEY,
        photo BLOB NOT NULL);
"""


def setup_tables(cur: sqlite3.Cursor, *args) -> None:
    """Helper to setup the tables in the database"""
    for arg in args:
        cur.execute(arg)


def raise_http_exception(status_code: int, message: str) -> HTTPException:
    """Helper to raise an HTTPException with a given status code and message"""
    logger.error(message)
    raise HTTPException(status_code=status_code, detail=message)


# ------------- #

app = FastAPI()

# set up logging
dictConfig(LogConfig().dict())
logger = logging.getLogger(App.config("LOGGER_NAME"))

# DB connections
conn = sqlite3.connect(App.config("SQLITE_DATABASE"))
cur = conn.cursor()

setup_tables(cur, _create_records_table, _create_photo_blob_table)


async def parse_body_bytes(request: Request):
    data: bytes = await request.body()
    return data


# API endpoints
@app.get("/")
def read_root():
    return {"API-Root": "Root path for LivingSnowProject test API"}


@app.get("/api/records")
async def get_records(
    limit: int = 20,
    before: str = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d"
    ),
):
    cur.execute(
        """SELECT json_object('id', id,
                                      'type', type,
                                      'name', name,
                                      'organization', organization,
                                      'date', date,
                                      'latitude', latitude,
                                      'longitude', longitude,
                                      'size', size,
                                      'color', color,
                                      'tubeId', tubeId,
                                      'locationDescription', locationDescription,
                                      'notes', notes,
                                      'photos', photos)
                    FROM records WHERE date < ? ORDER BY date DESC LIMIT ?""",
        (before, limit),
    )

    records = [json.loads(row[0]) for row in cur.fetchall()]
    for record in records:
        record["photos"] = json.loads(record["photos"])

    return records


@app.post("/api/records")
async def create_record(record: Record):
    # server assigns ID
    try:
        # get the current max ID
        cur.execute("SELECT MAX(id) FROM records")
        record.id = cur.fetchone()[0] + 1
        logger.info(f"New record ID: {record.id}")

        """
        Check to see if these are the cached photo objects which lack a size attribute and
        have URIs that are not numeric strings

        Example Photo from cached image:
            {
            "width": 1024,
            "uri": "file:///<lots-of-stuff>.jpg",
            "height": 1365
        }
        """
        if record.photos is not None and all(
            photo.size is None for photo in record.photos
        ):
            record.photos = None

        cur.execute(
            (
                """
            INSERT INTO records
            (id, type, name,
            organization, date,
            latitude, longitude,
            size, color, tubeId,
            locationDescription,
            notes, photos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """
            ),
            (
                record.id,
                record.type,
                record.name,
                record.organization,
                record.date,
                record.latitude,
                record.longitude,
                record.size,
                record.color,
                record.tubeId,
                record.locationDescription,
                record.notes,
                json.dumps(
                    [photo.dict() for photo in record.photos]
                    if record.photos is not None
                    else []
                ),
            ),
        )
        conn.commit()
    except Exception as e:
        logger.info(f"Rolling back transaction for record id {record.id}")
        conn.rollback()
        raise_http_exception(status_code=500, message=f"Error creating record: {e}")

    return record


@app.post("/api/records/{record_id}/photo")
async def add_photo(record_id: str, data: bytes = Depends(parse_body_bytes)):
    """
    # https://fastapi.tiangolo.com/advanced/using-request-directly/
    Since the client is sending the image bytes directly in the body, we need direct request access to get the body

    curl command to add a photo manually:

    curl -X POST -F "photo=@{filename}.jpg" http://localhost:8080/api/records/{record_id}/photo/
    """

    try:
        record_photos: List[PhotoEntry] = get_record_photo_uris(record_id)

        # get the current max ID and make a new incremental photo ID like the real API does
        cur.execute("SELECT MAX(CAST(uri AS INT)) FROM photos")
        photo_uri = cur.fetchone()[0] + 1
        record_photos = add_current_photo_uri(record_photos, data, photo_uri)

        # update the record with the new photo uris and add the photo to the blob storage table
        cur.execute(
            "UPDATE records SET photos = ? WHERE id = ?",
            (json.dumps([photo.dict() for photo in record_photos]), record_id),
        )
        cur.execute("INSERT INTO photos (uri, photo) VALUES (?, ?)", (photo_uri, data))

        conn.commit()
    except Exception as e:
        logger.info(
            f"Rolling back transaction for photo belonging to record {record_id}"
        )
        conn.rollback()
        raise_http_exception(500, f"Error adding photo: {e}")


@app.get("/api/blob/{photo_id}.jpg")
async def get_photo(photo_id: str) -> bytes:
    try:
        cur.execute("SELECT photo FROM photos WHERE uri = ?", (photo_id,))
        photo = cur.fetchone()
    except Exception as e:
        raise_http_exception(500, f"Error getting photo: {e}")

    if photo is None:
        raise_http_exception(404, f"Photo {photo_id} not found")

    return Response(content=photo[0], media_type="image/jpeg")


# a function that returns a list of Photo objects for a given record URI
def get_record_photo_uris(record_id: str) -> List[PhotoEntry]:
    cur.execute("SELECT photos FROM records WHERE id = ?", (record_id,))
    photos = cur.fetchone()[0]
    return [
        PhotoEntry(
            uri=photo["uri"],
            width=photo["width"],
            height=photo["height"],
            size=photo["size"],
        )
        for photo in json.loads(photos)
    ]


# function to add a new photo to a list of photos
def add_current_photo_uri(
    record_photos: List[PhotoEntry], photo: bytes, id
) -> List[PhotoEntry]:
    jpg_img: Image = Image.open(BytesIO(photo))
    width, height = jpg_img.size

    new_photo = PhotoEntry(uri=id, width=width, height=height, size=width * height)
    record_photos.append(new_photo)

    return record_photos
