from fastapi import FastAPI, HTTPException
from typing import Optional, List
import psycopg2
from psycopg2 import IntegrityError
import os
from datetime import date
from queries import(
    INSERT_CONTACT_QUERY,
    DELETE_CONTACT_QUERY,
    VIEW_CONTACTS_QUERY,
    INSERT_CALL_QUERY,
    VIEW_CALL_HISTORY_QUERY
)
from schemas import ContactCreate, Contact, CallCreate, Call
app = FastAPI(
    title="Phone Call Manager API",
    description="API for managing contacts and call history.",
    version="1.0.0"
)

conn=None

class ContactList:
    def __init__(self,connection):
        self.conn = connection
    def add_contact(self, name: str, phone_nr: str):
        try:
            with self.conn.cursor() as cur:
                cur.execute(INSERT_CONTACT_QUERY, (phone_nr, name))
            print(f"Contact - {name} and phone_number - {phone_nr} added successfully!")
            return{"phone_nr": phone_nr, "contact_name": name}
        except IntegrityError:
            self.conn.rollback()
            error_msg = f"A contact with {phone_nr} already exists."
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        except Exception as e:
            self.conn.rollback()
            error_msg = f"Error adding a contact {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
    def del_contact(self,phone_nr: str):
        try:
            with self.conn.cursor() as cur:
                cur.execute(DELETE_CONTACT_QUERY, (phone_nr,))
                result = cur.fetchone()
            if result:
                self.conn.commit()
                name = result[0]
                print(f"Contact - {name} and phone_number - {phone_nr} deleted.")
                return {"phone_nr": phone_nr, "contact_name": name}
            else:
                self.conn.rollback()
                error_msg = f"Contact with phone number {phone_nr} does not exist."
                print(error_msg)
                raise HTTPException(status_code=404, detail=error_msg)
        except HTTPException as he:
            raise he
        except Exception as e:
            self.conn.rollback()
            error_msg = f"Error deleting a contact {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def view_contacts(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute (VIEW_CONTACTS_QUERY)
                contacts = cur.fetchall()
            contact_list = [{"phone_nr": row[0], "contact_name": row[1]} for row in contacts]
            print(f"Contact list - {contact_list}!")
            return contact_list
        except Exception as e:
            error_msg = f"Error viewing contact list {e}."
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
class CallHistory:
    def __init__(self,connection):
        self.conn = connection
    def add_call(self, phone_nr: str, date: date,hour: int,minute: int,duration_seconds: int):
        try:
            with self.conn.cursor() as cur:
                cur.execute(INSERT_CALL_QUERY, (phone_nr, date, hour, minute, duration_seconds))
                call_id = cur.fetchone()[0]
            self.conn.commit()
            print(f"Call with ID {call_id} added!")
            return {
                "call_id": call_id,
                "phone_nr": phone_nr,
                "date": date,
                "hour": hour,
                "minute": minute,
                "duration_seconds": duration_seconds
            }
        except IntegrityError:
            self.conn.rollback()
            error_msg = f"Integrity error when adding call for {phone_nr}."
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        except Exception as e:
            self.conn.rollback()
            error_msg = f"Error adding call {e}."
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

    def view_call_history(self, phone_nr: Optional[str] = None):
        try:
            with self.conn.cursor() as cur:
                if phone_nr:
                    where_clause = "WHERE phone_nr = %s"
                    query = VIEW_CALL_HISTORY_QUERY.replace("{where_clause}", where_clause)
                    cur.execute(query, (phone_nr,))
                else:
                    where_clause = ""
                    query = VIEW_CALL_HISTORY_QUERY.replace("{where_clause}", where_clause)
                    cur.execute(query)
                call_history = cur.fetchall()
            call_list = [
                {
                    "call_id": row[0],
                    "phone_nr": row[1],
                    "date": row[2],
                    "hour": row[3],
                    "minute": row[4],
                    "duration_seconds": row[5]
                }
                for row in call_history
            ]
            print(f"Call history - {call_list}")
            return call_list
        except Exception as e:
            self.conn.rollback()
            error_msg = f"Error viewing call history {e}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

class PhoneCallManager:
    def __init__(self,connection):
        self.conn = connection
        self.contacts = ContactList(self.conn)
        self.call_history = CallHistory(self.conn)

    def close_connection(self):
        if self.conn:
            self.conn.close()
            print("Connection closed.")

phone_call_manager = None

@app.on_event("startup")
def startup():
    global conn, phone_call_manager
    try:
        print("DB_HOST:", os.getenv("DB_HOST"))
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        print('Database connection established.')
        phone_call_manager=PhoneCallManager(conn)
    except Exception as e:
        print(f"Error connecting to database {e}.")

@app.on_event("shutdown")
def shutdown_server():
      global conn, phone_call_manager
      if phone_call_manager:
          phone_call_manager.close_connection()
          print("Close db connection.")

@app.get("/ping", summary="Check server status.")
def ping():
    return {"message": "server work!"}

@app.get("/db_version")
def get_db_version():
    global conn
    if conn is None:
        raise HTTPException(status_code=500, detail= "Connection error!.")

    try:
        cur= conn.cursor()
        cur.execute("select version();")
        db_version = cur.fetchone()
        cur.close()
        return {"version": db_version[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/contacts", response_model=Contact, status_code=201, summary="Add a new contact. ")
def add_contact(contact: ContactCreate):
    global phone_call_manager
    if phone_call_manager is None:
        raise HTTPException(status_code=500, detail="Connection error!")
    return phone_call_manager.contacts.add_contact(contact.contact_name, contact.phone_nr)

@app.delete("/contacts/{phone_nr}", response_model=Contact, summary="Delete contact by phone number.")
def delete_contact(phone_nr: str):
    global phone_call_manager
    if phone_call_manager is None:
        raise HTTPException(status_code=500, detail="Database connection not established.")
    return phone_call_manager.contacts.del_contact(phone_nr)

@app.get("/contacts", response_model=List[Contact], summary="View list of contacts.")
def view_contacts():
    global phone_call_manager
    if phone_call_manager is None:
        raise HTTPException(status_code=500, detail="Database connection not established.")
    return phone_call_manager.contacts.view_contacts()

@app.post("/calls", response_model=Call, status_code=201, summary="Add a call record.")
def add_call(call: CallCreate):
    global phone_call_manager
    if phone_call_manager is None:
        raise HTTPException(status_code=500, detail="Database connection not established.")
    return phone_call_manager.call_history.add_call(
        phone_nr=call.phone_nr,
        date=call.date,
        hour=call.hour,
        minute=call.minute,
        duration_seconds=call.duration_seconds
    )

@app.get("/calls", response_model=List[Call], summary="View list of calls.")
def view_all_history(phone_nr: Optional[str] = None):
    global phone_call_manager
    if phone_call_manager is None:
        raise HTTPException(status_code=500, detail="Database connection not established.")
    return phone_call_manager.call_history.view_call_history(phone_nr)