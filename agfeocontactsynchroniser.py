"""AGFEO Contact Generator
Creates from different sources a VCF-File for Import
"""
import importlib
import inspect
import logging.handlers
import os
import sys

import toml as toml
from sqlalchemy import Column, Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base

from agfeo import Agfeo

__author__ = "Andreas Fendt"
__copyright__ = "Copyright 2022, Andreas Fendt"
__credits__ = ["Andreas Fendt"]
__maintainer__ = "Andreas Fendt"
__email__ = "info@fendt-it.com"
__status__ = "Production"

current_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

# configure logging
logger = logging.getLogger("agfeo-contact-synchroniser")
logger.setLevel(logging.INFO)
handler_stream = logging.StreamHandler(sys.stdout)
handler_file = logging.handlers.TimedRotatingFileHandler(
    os.path.join(current_path, "log", "agfeo-contact-synchroniser.log"),
    when="D", interval=1, backupCount=30
)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(process)d | %(message)s")
handler_stream.setFormatter(formatter)
handler_file.setFormatter(formatter)
logger.addHandler(handler_stream)
logger.addHandler(handler_file)


def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """
    Handler for unhandled exceptions that will write to the logs
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # call the default excepthook saved at __excepthook__
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


Base = declarative_base()


class AgfeoContactRelation(Base):
    __tablename__ = "agfeo_contact_relation"

    id = Column(Integer, primary_key=True)
    source_name = Column(String)
    source_id = Column(String)
    target_id = Column(String, index=True, unique=True)
    __table_args__ = (Index("source", "source_id", unique=True),)


def agfeo_block(total_size, block_size):
    """
    Generator for enumerating contacts
    """

    offset = 0
    while total_size > 0:
        size = min(total_size, block_size)
        yield offset, size
        offset += block_size
        total_size -= size


class AgfeoContactSynchroniser:

    def __init__(self):
        config = os.path.join(current_path, "config.toml")
        self.config = toml.load(config)
        self.engine = create_engine(f"sqlite:///{os.path.join(current_path, 'db', 'relation.db')}")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def run(self):
        """
        Run targets and write file
        """

        config_plugin = self.config["plugin"]

        # get contacts from plugins
        contacts = {}
        for plugin in config_plugin["enabled"]:
            plugin_module = importlib.import_module(f"plugins.contact_{plugin}")
            # noinspection PyUnresolvedReferences
            contacts.update(plugin_module.plugin_run(config_plugin[plugin], logger))

        agfeo = Agfeo(self.config["agfeo"])

        # login into agfeo
        logger.info("Agfeo: login to pbx")
        result = agfeo.login()
        if not result:
            logger.error(f"Agfeo: Error while logging in")
            exit()

        # get total size of agfeo contact store
        logger.info("Agfeo: get list of contacts in the pbx")
        result, total_size = agfeo.contact_get_size()
        if not result:
            logger.error("Agfeo: Error while retrieving number of contacts")
            exit()

        # get stored contacts
        block_size = 100
        agfeo_contacts = []
        for offset, size in agfeo_block(total_size, block_size):
            result, agfeo_contact = agfeo.contacts_get(offset, size)
            if not result:
                logger.error("Agfeo: Error while retrieving list of contacts")
                exit()
            agfeo_contacts = agfeo_contacts + agfeo_contact
        agfeo_contacts = {_agfeo_contact["uid"]: _agfeo_contact for _agfeo_contact in agfeo_contacts}

        # update or insert contacts from sources
        for source, contact in contacts.items():
            source_name, source_id = source

            # check if this contact is already linked to the pbx
            agfeo_contact_relation = self.session.query(AgfeoContactRelation) \
                .filter(and_(AgfeoContactRelation.source_name == source_name,
                             AgfeoContactRelation.source_id == source_id)) \
                .first()
            agfeo_contact_current = None
            if agfeo_contact_relation:
                agfeo_contact_current = agfeo_contacts.pop(agfeo_contact_relation.target_id, None)

            # insert or update the contact
            logger.info(f"Agfeo: {'update' if agfeo_contact_current else 'insert'} {contact.fn.value}")
            result, agfeo_contact = agfeo.contact_set(agfeo.vcard_to_data(contact, agfeo_contact_current))
            if not result:
                logger.error("Agfeo: Error while updating contact")

            if not agfeo_contact_relation:
                agfeo_contact_relation = AgfeoContactRelation()
                agfeo_contact_relation.source_name = source_name
                agfeo_contact_relation.source_id = source_id
                agfeo_contact_relation.target_id = agfeo_contact["uid"]
                self.session.add(agfeo_contact_relation)
                self.session.commit()

        # contacts which are no longer in the source databases they are now deleted from the target and database
        for contact_uid, contact in agfeo_contacts.items():
            agfeo.contact_delete(contact_uid)
            self.session.query(AgfeoContactRelation) \
                .where(AgfeoContactRelation.target_id == contact_uid) \
                .delete()
            self.session.commit()


if __name__ == "__main__":
    agfeo_contact_synchroniser = AgfeoContactSynchroniser()
    agfeo_contact_synchroniser.run()
