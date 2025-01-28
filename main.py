from fastapi import FastAPI, HTTPException, Depends, Request, Form, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import asyncpg
import os
from datetime import date
import logging

from starlette import status

from queries import (
    INSERT_CONTACT_QUERY,
    DELETE_CONTACT_QUERY,
    VIEW_CONTACTS_QUERY,
    INSERT_CALL_QUERY,
    VIEW_CALL_HISTORY_QUERY
)

from schemas import ContactCreate, Contact, CallCreate, Call

from dotenv import load_dotenv

load_dotenv()
app = FastAPI(
    title="Phone Call Manager API",
    description="API for managing contacts and call history.",
    version="1.0.0"
)

logging.basicConfig(
    level=logging.DEBUG,  # INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                min_size=1,
                max_size=10
            )
            logger.info("Database connection pool created.")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed.")

db = Database()

class ContactList:
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool

    async def add_contact(self, name: str, phone_nr: str):
        async with self.pool.acquire() as connection:
            try:
                await connection.execute(INSERT_CONTACT_QUERY, phone_nr, name)
                logger.info(f"Contact - {name} and phone_number - {phone_nr} added successfully!")
                return {"phone_nr": phone_nr, "contact_name": name}
            except asyncpg.exceptions.UniqueViolationError:
                error_msg = f"A contact with {phone_nr} already exists."
                logger.warning(error_msg)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
            except Exception as e:
                error_msg = f"Error adding a contact: {e}"
                logger.error(error_msg)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    async def del_contact(self, phone_nr: str):
        async with self.pool.acquire() as connection:
            try:
                result = await connection.fetchrow(DELETE_CONTACT_QUERY, phone_nr)
                if result:
                    name = result['contact_name']
                    logger.info(f"Contact - {name} and phone_number - {phone_nr} deleted.")
                    return {"phone_nr": phone_nr, "contact_name": name}
                else:
                    error_msg = f"Contact with phone number {phone_nr} does not exist."
                    logger.warning(error_msg)
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
            except HTTPException as he:
                raise he
            except Exception as e:
                error_msg = f"Error deleting a contact: {e}"
                logger.error(error_msg)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    async def view_contacts(self):
        async with self.pool.acquire() as connection:
            try:
                records = await connection.fetch(VIEW_CONTACTS_QUERY)
                contact_list = [{"phone_nr": record["phone_nr"], "contact_name": record["contact_name"]} for record in records]
                logger.info(f"Contact list - {contact_list}!")
                return contact_list
            except Exception as e:
                error_msg = f"Error viewing contact list: {e}."
                logger.error(error_msg)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

class CallHistory:
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool

    async def add_call(self, phone_nr: str, call_date: date, hour: int, minute: int, duration_seconds: int):
        async with self.pool.acquire() as connection:
            try:
                call_id = await connection.fetchval(
                    INSERT_CALL_QUERY,
                    phone_nr, call_date, hour, minute, duration_seconds
                )
                logger.info(f"Call with ID {call_id} added!")
                return {
                    "call_id": call_id,
                    "phone_nr": phone_nr,
                    "call_date": call_date,
                    "hour": hour,
                    "minute": minute,
                    "duration_seconds": duration_seconds
                }
            except asyncpg.exceptions.UniqueViolationError:
                error_msg = f"Integrity error when adding call for {phone_nr}."
                logger.warning(error_msg)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
            except Exception as e:
                error_msg = f"Error adding call: {e}."
                logger.error(error_msg)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    async def view_call_history(self, phone_nr: Optional[str] = None):
        async with self.pool.acquire() as connection:
            try:
                if phone_nr:
                    query = VIEW_CALL_HISTORY_QUERY.replace("{where_clause}", "WHERE phone_nr = $1")
                    records = await connection.fetch(query, phone_nr)
                else:
                    query = VIEW_CALL_HISTORY_QUERY.replace("{where_clause}", "")
                    records = await connection.fetch(query)
                call_list = [
                    {
                        "call_id": record["call_id"],
                        "phone_nr": record["phone_nr"],
                        "call_date": record["date"],
                        "hour": record["hour"],
                        "minute": record["minute"],
                        "duration_seconds": record["duration_seconds"]
                    }
                    for record in records
                ]
                logger.info(f"Call history - {call_list}")
                return call_list
            except Exception as e:
                error_msg = f"Error viewing call history: {e}"
                logger.error(error_msg)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

class PhoneCallManager:
    def __init__(self, pool: asyncpg.pool.Pool):
        self.pool = pool
        self.contacts = ContactList(self.pool)
        self.call_history = CallHistory(self.pool)

phone_call_manager: Optional[PhoneCallManager] = None

@app.on_event("startup")
async def startup_event():
    await db.connect()
    global phone_call_manager
    phone_call_manager = PhoneCallManager(db.pool)
    logger.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()
    logger.info("Application shutdown complete.")

def get_phone_call_manager():
    if phone_call_manager is None:
        logger.error("Phone call manager has not been initialized.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Phone call manager has not been initialized.")
    return phone_call_manager

api_router = APIRouter(prefix="/api", tags=["API"])

@api_router.post("/contacts", response_model=Contact, status_code=status.HTTP_201_CREATED, summary="Add a new contact.")
async def api_add_contact(contact: ContactCreate, manager: PhoneCallManager = Depends(get_phone_call_manager)):
    return await manager.contacts.add_contact(contact.contact_name, contact.phone_nr)

@api_router.delete("/contacts/{phone_nr}", response_model=Contact, summary="Delete contact by phone number.")
async def api_delete_contact(phone_nr: str, manager: PhoneCallManager = Depends(get_phone_call_manager)):
    return await manager.contacts.del_contact(phone_nr)

@api_router.get("/contacts", response_model=List[Contact], summary="List all contacts.")
async def api_view_contacts(manager: PhoneCallManager = Depends(get_phone_call_manager)):
    return await manager.contacts.view_contacts()

@api_router.post("/calls", response_model=Call, status_code=status.HTTP_201_CREATED, summary="Add a call record.")
async def api_add_call(call: CallCreate, manager: PhoneCallManager = Depends(get_phone_call_manager)):
    return await manager.call_history.add_call(
        phone_nr=call.phone_nr,
        call_date=call.call_date,
        hour=call.hour,
        minute=call.minute,
        duration_seconds=call.duration_seconds
    )

@api_router.get("/calls", response_model=List[Call], summary="List all calls.")
async def api_view_all_history(phone_nr: Optional[str] = None, manager: PhoneCallManager = Depends(get_phone_call_manager)):
    return await manager.call_history.view_call_history(phone_nr)

app.include_router(api_router)

@app.get("/", response_class=HTMLResponse, summary="Home page.")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/contacts", response_class=HTMLResponse, summary="View list of contacts.")
async def view_contacts(request: Request, manager: PhoneCallManager = Depends(get_phone_call_manager)):
    contacts = await manager.contacts.view_contacts()
    message = request.query_params.get("message")
    error = request.query_params.get("error")
    return templates.TemplateResponse("contacts.html", {
        "request": request,
        "contacts": contacts,
        "message": message,
        "error": error
    })

@app.get("/contacts/add", response_class=HTMLResponse, summary="Add Contact Form")
async def add_contact_form(request: Request):
    return templates.TemplateResponse("add_contact.html", {"request": request})

@app.post("/contacts/add", response_class=HTMLResponse, summary="Add Contact.")
async def add_contact(
        request: Request,
        contact_name: str = Form(...),
        phone_nr: str = Form(...),
        manager: PhoneCallManager = Depends(get_phone_call_manager)
):
    try:
        await manager.contacts.add_contact(contact_name, phone_nr)
        return RedirectResponse(url="/contacts?message=Contact added successfully.", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        return RedirectResponse(url=f"/contacts/add?error={e.detail}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/contacts/delete/{phone_nr}", summary="Delete Contact.")
async def delete_contact(phone_nr: str, manager: PhoneCallManager = Depends(get_phone_call_manager)):
    try:
        await manager.contacts.del_contact(phone_nr)
        return RedirectResponse(url="/contacts?message=Contact deleted successfully.", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        return RedirectResponse(url=f"/contacts?error={e.detail}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/calls", response_class=HTMLResponse, summary="View Call History.")
async def view_calls(request: Request, manager: PhoneCallManager = Depends(get_phone_call_manager)):
    phone_nr = request.query_params.get("phone_nr")
    calls = await manager.call_history.view_call_history(phone_nr)
    message = request.query_params.get("message")
    error = request.query_params.get("error")
    return templates.TemplateResponse("calls.html", {
        "request": request,
        "calls": calls,
        "message": message,
        "error": error
    })

@app.get("/calls/add", response_class=HTMLResponse, summary="Add Call Form.")
async def add_call_form(request: Request):
    return templates.TemplateResponse("add_call.html", {"request": request})

@app.post("/calls/add", response_class=HTMLResponse, summary="Add Call.")
async def add_call(
        request: Request,
        phone_nr: str = Form(...),
        call_date: date = Form(...),
        hour: int = Form(...),
        minute: int = Form(...),
        duration_seconds: int = Form(...),
        manager: PhoneCallManager = Depends(get_phone_call_manager)
):
    try:
        await manager.call_history.add_call(phone_nr, call_date, hour, minute, duration_seconds)
        return RedirectResponse(url="/calls?message=Call added successfully.", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        return RedirectResponse(url=f"/calls/add?error={e.detail}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/ping", summary="Check server status.")
async def ping():
    return {"message": "server work!"}

@app.get("/db_version")
async def get_db_version():
    async with db.pool.acquire() as connection:
        try:
            db_version = await connection.fetchval("SELECT version();")
            return {"version": db_version}
        except Exception as e:
            logger.error(f"Error fetching DB version: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))