from typing import Dict

import vobject.vcard
from exchangelib import Credentials, Account


def plugin_run(config: dict, logger) -> Dict:
    """
    Get all Exchange contacts
    """

    # get exchange contacts
    logger.info("Exchange: create Credentials")
    exchange_credentials = Credentials(config["username"], config["password"])

    logger.info("Exchange: create Account")
    exchange_account = Account(config["username"], credentials=exchange_credentials, autodiscover=True)

    exchange_contacts = {}
    logger.info("Exchange: get all Contacts")
    for exchange_contact in exchange_account.contacts.all():
        try:
            logger.info(f"Exchange: read contact {exchange_contact.display_name}")
            v = vobject.readOne(bytes(exchange_contact.mime_content).decode())
            exchange_contacts[("exchange", exchange_contact.id)] = v
        except:
            logger.exception("Exchange: Error while reading contact")

    return exchange_contacts
