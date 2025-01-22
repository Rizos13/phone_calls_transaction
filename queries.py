INSERT_CONTACT_QUERY = """
    INSERT INTO contact_list (phone_nr, contact_name)
    VALUES (%s, %s);
"""

DELETE_CONTACT_QUERY = """
    DELETE FROM contact_list
    WHERE phone_nr = %s;
    RETURNING contact_name;
"""

VIEW_CONTACTS_QUERY = """
    SELECT phone_nr, contact_name
    FROM contact_list
    ORDER BY contact_name ASC;
"""

INSERT_CALL_QUERY = """
    INSERT INTO call_history (phone_nr, date, hour, minute, duration_seconds)
    VALUES (%s, %s, %s, %s, %s);
    RETURNING call_id;
"""

VIEW_CALL_HISTORY_QUERY = """
    SELECT call_id, phone_nr, date, hour, minute, duration_seconds
    FROM call_history
    {where_clause}
    ORDER BY date DESC, hour DESC, minute DESC;
"""