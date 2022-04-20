from typing import Dict

import phonenumbers.carrier
import vobject.vcard
from sqlalchemy import create_engine, Table, MetaData, select, and_, or_


def plugin_run(config: dict, logger) -> Dict:
    """
    Process all Sage contacts
    """

    # get sage contacts
    logger.info("Sage: connecting to the database")
    engine = create_engine(
        f"mssql+pyodbc://{config['username']}:{config['password']}@"
        f"{config['hostname']}\\{config['instance']}/{config['database']}"
        f"?driver=ODBC+Driver+13+for+SQL+Server"
    )
    conn = engine.connect()

    metadata_obj = MetaData()
    customers = Table("T_KND", metadata_obj, autoload_with=engine)

    # noinspection PyPropertyAccess
    stmt = select(
        (customers.c.Nummer).label("id"),
        (customers.c.Name).label("name"),
        (customers.c.Telefon1).label("phone_1"),
        (customers.c.Telefon2).label("phone_2")
    ).where(
        and_(customers.c.Name != None,
             or_(customers.c.Telefon1 != None, customers.c.Telefon1 != None))
    ).order_by(customers.c.Name)

    sage_contacts = {}

    logger.info("Sage: listing all contacts")
    for row in conn.execute(stmt):
        sage_vcard = vobject.vCard()

        sage_vcard_object = sage_vcard.add("n")
        sage_vcard_object.value = vobject.vcard.Name(family=row.name)

        sage_vcard_object = sage_vcard.add("fn")
        sage_vcard_object.value = row.name

        found = False
        for number in [row.phone_1, row.phone_2]:
            if number is None or number == "":
                continue

            try:
                phonenumber = phonenumbers.parse(number, "DE")
            except:
                logger.exception(f"Sage: error while parsing {number}")
                continue

            if not phonenumbers.is_valid_number(phonenumber) or not phonenumbers.is_possible_number(phonenumber):
                continue

            found = True
            phonenumber_str = phonenumbers.format_number(phonenumber, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            sage_vcard_object = sage_vcard.add("tel")

            sage_vcard_object.type_param = "CELL" \
                if phonenumbers.carrier._is_mobile(phonenumbers.phonenumberutil.number_type(phonenumber)) \
                else "WORK"
            sage_vcard_object.value = phonenumber_str

        if found:
            logger.info(f"Sage: read contact {sage_vcard.fn.value}")
            sage_contacts[("sage", row.id)] = sage_vcard

    return sage_contacts
