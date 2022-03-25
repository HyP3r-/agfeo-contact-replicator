"""AGEFO Contact Generator
Creates from different sources a VCF-File for Import
"""
import inspect
import os

from exchangelib import Credentials, Account
from sqlalchemy import create_engine, Table, MetaData, select, and_, or_
import vobject.vcard
import phonenumbers.carrier

__author__ = "Andreas Fendt"
__copyright__ = "Copyright 2022, Andreas Fendt"
__credits__ = ["Andreas Fendt"]
__maintainer__ = "Andreas Fendt"
__email__ = "info@fendt-it.com"
__status__ = "Production"

current_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

# get exchange contacts
exchange_credentials = Credentials('info@elektro-fendt.de', 'CyTfBKPmDZ6yJ1JpzKYY')
exchange_account = Account('info@elektro-fendt.de', credentials=exchange_credentials, autodiscover=True)
exchange_contacts = [contact for contact in exchange_account.contacts.all()]
exchange_contacts_str = "".join([bytes(exchange_contact.mime_content).decode()
                                 for exchange_contact in exchange_contacts])

# get sage contacts
engine = create_engine("mssql+pyodbc://sa:Fezie1958@EF-PC01\\SAGEHW/Handwerk?driver=ODBC+Driver+13+for+SQL+Server",
                       echo=True)
conn = engine.connect()

metadata_obj = MetaData()
customers = Table("T_KND", metadata_obj, autoload_with=engine)

# noinspection PyPropertyAccess
stmt = select(
    (customers.c.Name).label("name"),
    (customers.c.Telefon1).label("phone_1"),
    (customers.c.Telefon2).label("phone_2")
).where(
    and_(customers.c.Name != None,
         or_(customers.c.Telefon1 != None, customers.c.Telefon1 != None))
).order_by(customers.c.Name)

sage_contacts = []

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
        sage_contacts.append(sage_vcard.serialize())

sage_contacts_str = "".join(sage_contacts)

# write result to file
with open(os.path.join(current_path, "result", "result.vcf"), "w", encoding="utf8", newline="") as f:
    f.write("".join([exchange_contacts_str, sage_contacts_str]))
